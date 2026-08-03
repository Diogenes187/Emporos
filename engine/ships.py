"""Authoritative ship acquisition and initial vessel-state construction."""

from __future__ import annotations

from dataclasses import dataclass
import psycopg


@dataclass(frozen=True)
class ShipAcquisitionResult:
    command_public_id: str
    campaign_public_id: str
    ship_public_id: str
    owner_actor_public_id: str
    name: str
    registration_identifier: str | None
    class_code: str
    component_count: int
    crew_position_count: int
    resource_count: int
    replayed: bool


def _load(connection, command_id, command_public_id, replayed):
    row = connection.execute(
        """
        SELECT campaign.public_id,ship.public_id,actor.public_id,
               receipt.ship_name,receipt.registration_identifier,
               class.class_code,receipt.component_count,
               receipt.crew_position_count,receipt.resource_count
          FROM cmd_ship_acquisition_receipt receipt
          JOIN camp_campaign campaign USING (campaign_id)
          JOIN ship_ship ship USING (ship_id)
          JOIN actor_actor actor ON actor.actor_id=receipt.owner_actor_id
          JOIN ship_class class
            ON class.ship_class_rule_id=receipt.ship_class_rule_id
         WHERE receipt.command_id=%s
        """, (command_id,)
    ).fetchone()
    return ShipAcquisitionResult(
        str(command_public_id),str(row[0]),str(row[1]),str(row[2]),
        row[3],row[4],row[5],row[6],row[7],row[8],replayed,
    )


def acquire_ship_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, campaign_public_id: str,
    owner_actor_public_id: str, class_code: str, ship_name: str,
    registration_identifier: str | None = None,
) -> ShipAcquisitionResult:
    """Create the vessel, identity, systems, resources, stations and ownership."""
    name=ship_name.strip()
    registration=(registration_identifier or "").strip() or None
    if not name: raise ValueError("Ship name cannot be blank")
    if not idempotency_key.strip(): raise ValueError("Idempotency key cannot be blank")
    with connection.transaction():
        existing=connection.execute(
            "SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",
            (initiator_reference,idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("acquire_ship","completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load(connection,existing[0],existing[1],True)
        campaign=connection.execute(
            "SELECT campaign_id FROM camp_campaign WHERE public_id=%s AND owner_reference=%s AND campaign_status='active' FOR UPDATE",
            (campaign_public_id,initiator_reference),
        ).fetchone()
        if campaign is None:
            raise PermissionError("Campaign is absent or not controlled by this player")
        owner=connection.execute(
            "SELECT actor_id FROM actor_actor WHERE public_id=%s AND campaign_id=%s FOR UPDATE",
            (owner_actor_public_id,campaign[0]),
        ).fetchone()
        if owner is None: raise ValueError("Owner is not a character in this campaign")
        vessel_class=connection.execute(
            "SELECT ship_class_rule_id,hull_points,structure_points,power_rating FROM ship_class WHERE class_code=%s",
            (class_code,),
        ).fetchone()
        if vessel_class is None: raise ValueError("Unknown ship class")
        command_id,command_public=connection.execute(
            "INSERT INTO cmd_command (command_type,initiator_reference,idempotency_key) VALUES ('acquire_ship',%s,%s) RETURNING command_id,public_id",
            (initiator_reference,idempotency_key),
        ).fetchone()
        item_id=connection.execute(
            "INSERT INTO inv_item_instance (campaign_id,item_rule_id,instance_name,serial_identifier,source_command_id) VALUES (%s,%s,%s,%s,%s) RETURNING item_instance_id",
            (campaign[0],vessel_class[0],name,registration,command_id),
        ).fetchone()[0]
        ship_id,ship_public=connection.execute(
            """INSERT INTO ship_ship
               (campaign_id,ship_class_rule_id,inventory_item_instance_id,name,
                registration_identifier,hull_current,structure_current,commissioned_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,clock_timestamp())
               RETURNING ship_id,public_id""",
            (campaign[0],vessel_class[0],item_id,name,registration,vessel_class[1],vessel_class[2]),
        ).fetchone()
        component_count=connection.execute(
            """WITH made AS (
                INSERT INTO ship_component
                    (ship_id,campaign_id,class_component_id,component_rule_id,
                     component_identifier,rating)
                SELECT %s,%s,template.ship_class_component_id,
                       template.component_rule_id,
                       definition.component_code||'-'||lpad(series::text,2,'0'),
                       template.rating
                  FROM ship_class_component template
                  JOIN ship_component_definition definition
                    ON definition.component_rule_id=template.component_rule_id
                  CROSS JOIN LATERAL generate_series(1,template.quantity) series
                 WHERE template.ship_class_rule_id=%s
                RETURNING 1) SELECT count(*) FROM made""",
            (ship_id,campaign[0],vessel_class[0]),
        ).fetchone()[0]
        crew_count=connection.execute(
            """WITH made AS (
                INSERT INTO ship_crew_position
                    (ship_id,campaign_id,crew_position_rule_id,position_identifier)
                SELECT %s,%s,template.crew_position_rule_id,
                       definition.position_code||'-'||lpad(series::text,2,'0')
                  FROM ship_class_crew_position template
                  JOIN ship_crew_position_definition definition
                    ON definition.crew_position_rule_id=template.crew_position_rule_id
                  CROSS JOIN LATERAL generate_series(1,template.position_count) series
                 WHERE template.ship_class_rule_id=%s
                UNION ALL
                SELECT %s,%s,definition.crew_position_rule_id,'master-01'
                  FROM ship_crew_position_definition definition
                 WHERE definition.position_code='master'
                   AND NOT EXISTS (
                       SELECT 1 FROM ship_class_crew_position template
                       JOIN ship_crew_position_definition existing
                         ON existing.crew_position_rule_id=template.crew_position_rule_id
                      WHERE template.ship_class_rule_id=%s
                        AND existing.position_code='master'
                   )
                RETURNING 1) SELECT count(*) FROM made""",
            (ship_id,campaign[0],vessel_class[0],ship_id,campaign[0],vessel_class[0]),
        ).fetchone()[0]
        resource_count=connection.execute(
            """WITH capacities(resource_type_code,capacity) AS (
                SELECT 'refined_fuel',characteristic_value
                  FROM ship_class_characteristic
                 WHERE ship_class_rule_id=%s AND characteristic_code='fuel_tons'
                UNION ALL SELECT 'power',%s WHERE %s>0
            ), made AS (
                INSERT INTO ship_resource
                    (ship_id,campaign_id,resource_type_code,current_quantity,
                     capacity_quantity,source_command_id)
                SELECT %s,%s,resource_type_code,capacity,capacity,%s
                  FROM capacities WHERE capacity>0 RETURNING 1)
                SELECT count(*) FROM made""",
            (vessel_class[0],vessel_class[3],vessel_class[3],ship_id,campaign[0],command_id),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO ship_legal_interest (ship_id,campaign_id,interest_kind,actor_id,share_basis_points,source_command_id) VALUES (%s,%s,'ownership',%s,10000,%s)",
            (ship_id,campaign[0],owner[0],command_id),
        )
        connection.execute(
            "INSERT INTO ship_operational_control (ship_id,campaign_id,actor_id,control_basis,source_command_id) VALUES (%s,%s,%s,'owner',%s)",
            (ship_id,campaign[0],owner[0],command_id),
        )
        captain=connection.execute(
            """SELECT position.ship_crew_position_id
                 FROM ship_crew_position position
                 JOIN ship_crew_position_definition definition
                   ON definition.crew_position_rule_id=position.crew_position_rule_id
                WHERE position.ship_id=%s AND definition.position_code='master'
                ORDER BY position.ship_crew_position_id LIMIT 1""", (ship_id,)
        ).fetchone()
        if captain:
            connection.execute(
                "INSERT INTO ship_crew_assignment (ship_crew_position_id,ship_id,campaign_id,actor_id,source_command_id) VALUES (%s,%s,%s,%s,%s)",
                (captain[0],ship_id,campaign[0],owner[0],command_id),
            )
        connection.execute(
            """INSERT INTO cmd_ship_acquisition_receipt
               (command_id,campaign_id,ship_id,owner_actor_id,
                inventory_item_instance_id,ship_class_rule_id,ship_name,
                registration_identifier,component_count,crew_position_count,
                resource_count,ship_version_after)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)""",
            (command_id,campaign[0],ship_id,owner[0],item_id,vessel_class[0],name,
             registration,component_count,crew_count,resource_count),
        )
        connection.execute("INSERT INTO cmd_domain_event (command_id,event_order,event_type) VALUES (%s,1,'ship_acquired')",(command_id,))
        connection.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
        return _load(connection,command_id,command_public,False)
