"""Read-only Base Cepheus projections for the Emporos web application."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from typing import Any

import psycopg
from psycopg.rows import dict_row


def database_url() -> str | None:
    return os.environ.get("EMPOROS_DATABASE_URL") or os.environ.get(
        "BASE_CEPHEUS_DATABASE_URL"
    )


@dataclass(frozen=True)
class CampaignSummary:
    public_id: str
    name: str
    play_mode: str
    status: str
    day_number: int
    actor_count: int
    ship_count: int
    system_count: int


class CampaignReader:
    """Produces UI projections without acquiring mutation authority."""

    def __init__(self, url: str | None = None):
        self.url = url if url is not None else database_url()

    @property
    def configured(self) -> bool:
        return bool(self.url)

    def _connect(self):
        if not self.url:
            raise RuntimeError("No Emporos database URL is configured")
        return psycopg.connect(
            self.url,
            row_factory=dict_row,
            options="-c default_transaction_read_only=on",
        )

    def campaigns(self, limit: int = 30) -> list[CampaignSummary]:
        if not self.url:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT campaign.public_id::text AS public_id,
                       campaign.name,campaign.play_mode,
                       campaign.campaign_status AS status,
                       COALESCE(clock.day_number,0) AS day_number,
                       (SELECT count(*) FROM actor_actor actor
                        WHERE actor.campaign_id=campaign.campaign_id) AS actor_count,
                       (SELECT count(*) FROM ship_ship ship
                        WHERE ship.campaign_id=campaign.campaign_id) AS ship_count,
                       (SELECT count(*) FROM loc_star_system system
                        WHERE system.campaign_id=campaign.campaign_id) AS system_count
                FROM camp_campaign campaign
                LEFT JOIN camp_clock clock USING (campaign_id)
                WHERE campaign.campaign_status='active'
                ORDER BY campaign.created_at DESC,campaign.campaign_id DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return [CampaignSummary(**row) for row in rows]

    def campaign(self, public_id: str) -> dict[str, Any] | None:
        if not self.url:
            return None
        with self._connect() as connection:
            campaign = connection.execute(
                """
                SELECT campaign.campaign_id,campaign.public_id::text AS public_id,
                       campaign.name,campaign.play_mode,
                       campaign.campaign_status AS status,
                       COALESCE(clock.day_number,0) AS day_number,
                       COALESCE(clock.second_of_day,0) AS second_of_day
                FROM camp_campaign campaign
                LEFT JOIN camp_clock clock USING (campaign_id)
                WHERE campaign.public_id=%s
                """,
                (public_id,),
            ).fetchone()
            if campaign is None:
                return None
            campaign_id = campaign.pop("campaign_id")
            actors = connection.execute(
                """
                SELECT actor.public_id::text AS public_id,actor.name,
                       actor.concurrency_version,
                       COALESCE(profile.character_name,actor.name) AS character_name,
                       position.name AS location_name,
                       lifepath.age_years,lifepath.lifepath_status,
                       (SELECT count(*) FROM actor_skill skill
                        WHERE skill.actor_id=actor.actor_id) AS skill_count,
                       COALESCE((
                           SELECT jsonb_agg(jsonb_build_object(
                               'code',rule.rule_code,
                               'name',rule.name,
                               'abbreviation',definition.abbreviation,
                               'current',score.current_value,
                               'maximum',score.maximum_value
                           ) ORDER BY definition.display_order)
                           FROM actor_characteristic score
                           JOIN rule_characteristic definition
                             ON definition.rule_id=score.characteristic_rule_id
                           JOIN rule_rule rule ON rule.rule_id=definition.rule_id
                           WHERE score.actor_id=actor.actor_id
                       ),'[]'::jsonb) AS characteristics
                FROM actor_actor actor
                LEFT JOIN actor_current_character_profile profile
                  ON profile.actor_id=actor.actor_id
                LEFT JOIN loc_actor_position current_position
                  ON current_position.actor_id=actor.actor_id
                 AND current_position.position_status='current'
                LEFT JOIN loc_location position
                  ON position.location_id=current_position.location_id
                LEFT JOIN actor_lifepath_state lifepath
                  ON lifepath.actor_id=actor.actor_id
                WHERE actor.campaign_id=%s
                ORDER BY actor.name
                """,
                (campaign_id,),
            ).fetchall()
            ships = connection.execute(
                """
                SELECT ship.public_id::text AS public_id,ship.name,
                       ship.registration_identifier,ship.lifecycle_status,
                       ship.legal_status,ship.hull_current,ship.structure_current,
                       class.class_code,class.hull_tons,class.hull_points,
                       class.structure_points,class.jump_rating,
                       class.maneuver_rating,class.cargo_capacity_tons,
                       location.name AS location_name,location.public_id::text AS location_public_id,
                       (SELECT count(*) FROM ship_component component WHERE component.ship_id=ship.ship_id AND component.operational_status<>'removed') AS component_count,
                       (SELECT count(*) FROM ship_crew_position position WHERE position.ship_id=ship.ship_id AND position.position_status<>'removed') AS crew_position_count,
                       (SELECT actor.name FROM ship_legal_interest interest JOIN actor_actor actor ON actor.actor_id=interest.actor_id WHERE interest.ship_id=ship.ship_id AND interest.interest_kind='ownership' AND interest.ended_at IS NULL LIMIT 1) AS owner_name,
                       COALESCE((SELECT jsonb_agg(jsonb_build_object('code',resource.resource_type_code,'current',resource.current_quantity,'capacity',resource.capacity_quantity) ORDER BY resource.resource_type_code) FROM ship_resource resource WHERE resource.ship_id=ship.ship_id),'[]'::jsonb) AS resources
                FROM ship_ship ship
                JOIN ship_class class
                  ON class.ship_class_rule_id=ship.ship_class_rule_id
                LEFT JOIN loc_location location
                  ON location.location_id=ship.current_location_id
                WHERE ship.campaign_id=%s
                ORDER BY ship.name
                """,
                (campaign_id,),
            ).fetchall()
            crew_positions=connection.execute("""SELECT position.ship_crew_position_id,ship.public_id::text AS ship_public_id,ship.name AS ship_name,definition.position_name,definition.standard_monthly_salary_minor,actor.name AS assigned_actor_name FROM ship_crew_position position JOIN ship_ship ship USING(ship_id) JOIN ship_crew_position_definition definition ON definition.crew_position_rule_id=position.crew_position_rule_id LEFT JOIN ship_crew_assignment assignment ON assignment.ship_crew_position_id=position.ship_crew_position_id AND assignment.duty_status='active' LEFT JOIN actor_actor actor ON actor.actor_id=assignment.actor_id WHERE position.campaign_id=%s AND position.position_status='available' ORDER BY ship.name,position.ship_crew_position_id""",(campaign_id,)).fetchall()
            systems = connection.execute(
                """
                SELECT system_location.public_id::text AS public_id,
                       system_location.name,system.hex_column,system.hex_row,
                       sector_location.name AS sector_name,
                       system.discovery_status,
                       profile.starport_code,profile.size_code,
                       profile.atmosphere_code,profile.hydrographics_code,
                       profile.population_code,profile.government_code,
                       profile.law_level_code,profile.technology_level
                FROM loc_star_system system
                JOIN loc_location system_location
                  ON system_location.location_id=system.location_id
                JOIN loc_location sector_location
                  ON sector_location.location_id=system.sector_location_id
                LEFT JOIN LATERAL (
                    SELECT world.*
                    FROM loc_celestial_body body
                    JOIN loc_world_profile world
                      ON world.location_id=body.location_id
                     AND world.profile_status='current'
                    WHERE body.system_location_id=system.location_id
                    ORDER BY body.orbit_order NULLS LAST,body.location_id
                    LIMIT 1
                ) profile ON true
                WHERE system.campaign_id=%s
                ORDER BY system.hex_column,system.hex_row
                """,
                (campaign_id,),
            ).fetchall()
            journeys=connection.execute("""SELECT journey.public_id::text AS public_id,journey.name,journey.journey_status,ship.name AS ship_name,origin.name AS origin_name,destination.name AS destination_name,leg.distance_value AS distance_parsecs,navigation.succeeded AS route_succeeded,attempt.jump_outcome,attempt.duration_hours,execution.execution_status FROM journey_journey journey JOIN ship_ship ship ON ship.ship_id=journey.ship_id LEFT JOIN journey_leg leg ON leg.journey_id=journey.journey_id AND leg.leg_order=1 LEFT JOIN loc_location origin ON origin.location_id=leg.origin_location_id LEFT JOIN loc_location destination ON destination.location_id=leg.destination_location_id LEFT JOIN LATERAL (SELECT succeeded FROM journey_navigation_solution WHERE journey_leg_id=leg.journey_leg_id AND operation_kind='jump_route' ORDER BY navigation_solution_id DESC LIMIT 1) navigation ON true LEFT JOIN journey_jump_attempt attempt ON attempt.journey_leg_id=leg.journey_leg_id LEFT JOIN journey_leg_execution execution ON execution.journey_leg_id=leg.journey_leg_id WHERE journey.campaign_id=%s ORDER BY journey.created_at DESC LIMIT 20""",(campaign_id,)).fetchall()
            markets=connection.execute("""SELECT market.public_id::text AS public_id,market.name,market.market_kind,world.name AS world_name,system_location.public_id::text AS system_public_id,session.market_session_id,session.expires_day,COALESCE((SELECT jsonb_agg(jsonb_build_object('stock_id',stock.stock_id,'code',good.good_code,'name',rule.name,'kind',good.good_kind,'quantity',stock.quantity_tons,'base_price',good.base_price_credits) ORDER BY good.good_kind,good.good_code) FROM mkt_stock stock JOIN rule_trade_good good ON good.trade_good_rule_id=stock.trade_good_rule_id JOIN rule_rule rule ON rule.rule_id=good.trade_good_rule_id WHERE stock.market_session_id=session.market_session_id AND stock.stock_status='available'),'[]'::jsonb) AS stock FROM mkt_market market JOIN loc_location world ON world.location_id=market.location_id JOIN loc_celestial_body body ON body.location_id=world.location_id JOIN loc_location system_location ON system_location.location_id=body.system_location_id LEFT JOIN LATERAL (SELECT current.* FROM mkt_session current WHERE current.market_id=market.market_id AND current.session_status='open' ORDER BY current.opened_day DESC,current.market_session_id DESC LIMIT 1) session ON true WHERE market.campaign_id=%s AND market.market_status='active' ORDER BY market.name""",(campaign_id,)).fetchall()
            broker_quotes=connection.execute("""SELECT command.public_id::text AS command_public_id,actor.public_id::text AS actor_public_id,actor.name AS actor_name,good.good_code,rule.name AS good_name,receipt.check_total,receipt.price_percent,command.completed_at,stock.stock_id FROM cmd_broker_operation_receipt receipt JOIN cmd_command command USING(command_id) JOIN actor_actor actor ON actor.actor_id=receipt.actor_id JOIN rule_trade_good good ON good.trade_good_rule_id=receipt.trade_good_rule_id JOIN rule_rule rule ON rule.rule_id=good.trade_good_rule_id LEFT JOIN mkt_stock stock ON stock.market_session_id=receipt.market_session_id AND stock.trade_good_rule_id=receipt.trade_good_rule_id AND stock.stock_status='available' WHERE receipt.campaign_id=%s AND receipt.operation_code='determine-purchase-price' ORDER BY command.completed_at DESC LIMIT 20""",(campaign_id,)).fetchall()
            purchases=connection.execute("""SELECT actor.name AS actor_name,ship.name AS ship_name,rule.name AS good_name,receipt.quantity_tons,receipt.unit_price_minor,receipt.total_price_minor FROM cmd_trade_goods_purchase_receipt receipt JOIN actor_actor actor USING(actor_id) JOIN ship_ship ship USING(ship_id) JOIN rule_rule rule ON rule.rule_id=receipt.trade_good_rule_id WHERE receipt.campaign_id=%s ORDER BY receipt.command_id DESC""",(campaign_id,)).fetchall()
            cargo_lots=connection.execute("""SELECT lot.lot_id,good.good_code,rule.name AS good_name,placement.quantity,ship.public_id::text AS ship_public_id,ship.name AS ship_name,actor.public_id::text AS actor_public_id FROM cmd_trading_preparation_receipt setup JOIN actor_actor actor USING(actor_id) JOIN ship_ship ship USING(ship_id) JOIN inv_container_lot placement ON placement.container_id=setup.cargo_container_id JOIN inv_lot lot USING(lot_id) JOIN rule_trade_good good ON good.trade_good_rule_id=lot.item_rule_id JOIN rule_rule rule ON rule.rule_id=good.trade_good_rule_id WHERE setup.campaign_id=%s AND lot.lot_status='active' ORDER BY ship.name,rule.name""",(campaign_id,)).fetchall()
            sale_quotes=connection.execute("""SELECT command.public_id::text AS command_public_id,actor.public_id::text AS actor_public_id,good.good_code,receipt.price_percent,receipt.market_session_id FROM cmd_broker_operation_receipt receipt JOIN cmd_command command USING(command_id) JOIN actor_actor actor ON actor.actor_id=receipt.actor_id JOIN rule_trade_good good ON good.trade_good_rule_id=receipt.trade_good_rule_id WHERE receipt.campaign_id=%s AND receipt.operation_code='determine-sale-price' ORDER BY command.completed_at DESC LIMIT 20""",(campaign_id,)).fetchall()
            sales=connection.execute("""SELECT actor.name AS actor_name,ship.name AS ship_name,rule.name AS good_name,receipt.quantity_tons,receipt.total_price_minor FROM cmd_trade_goods_sale_receipt receipt JOIN actor_actor actor USING(actor_id) JOIN ship_ship ship USING(ship_id) JOIN rule_rule rule ON rule.rule_id=receipt.trade_good_rule_id WHERE receipt.campaign_id=%s ORDER BY receipt.command_id DESC""",(campaign_id,)).fetchall()
            trading_accounts=connection.execute("""SELECT actor.public_id::text AS actor_public_id,actor.name AS actor_name,ship.public_id::text AS ship_public_id,ship.name AS ship_name,account.public_id::text AS account_public_id,balance.balance_minor,receipt.cargo_container_id FROM cmd_trading_preparation_receipt receipt JOIN actor_actor actor USING(actor_id) JOIN ship_ship ship USING(ship_id) JOIN fin_account account ON account.account_id=receipt.trader_account_id JOIN fin_account_balance balance ON balance.account_id=account.account_id WHERE receipt.campaign_id=%s ORDER BY receipt.command_id""",(campaign_id,)).fetchall()
            refuelings=connection.execute("""SELECT ship.name AS ship_name,actor.name AS actor_name,receipt.fuel_type_code,receipt.tons_acquired,receipt.total_price_minor,receipt.quantity_after,command.completed_at FROM cmd_ship_refueling_receipt receipt JOIN ship_ship ship USING(ship_id) JOIN actor_actor actor USING(actor_id) JOIN cmd_command command USING(command_id) WHERE receipt.campaign_id=%s ORDER BY receipt.command_id DESC LIMIT 20""",(campaign_id,)).fetchall()
            ship_expenses=connection.execute("""SELECT ship.name AS ship_name,receipt.operating_cost_code,receipt.quantity,receipt.amount_minor,command.completed_at FROM cmd_ship_operating_expense_receipt receipt JOIN ship_ship ship USING(ship_id) JOIN cmd_command command USING(command_id) WHERE receipt.campaign_id=%s ORDER BY receipt.command_id DESC LIMIT 20""",(campaign_id,)).fetchall()
            journal_notes=connection.execute("SELECT public_id::text AS public_id,title,note_kind,note_text,ai_memory_enabled,created_at FROM camp_journal_note WHERE campaign_id=%s ORDER BY created_at DESC LIMIT 100",(campaign_id,)).fetchall()
            session_archives=connection.execute("SELECT public_id::text AS public_id,title,campaign_day,transcript_text,ai_memory_enabled,archived_at FROM camp_session_archive WHERE campaign_id=%s ORDER BY archived_at DESC LIMIT 100",(campaign_id,)).fetchall()
            crew_payrolls=connection.execute("""SELECT ship.name AS ship_name,receipt.payroll_day,receipt.total_amount_minor,count(line.line_order) AS crew_paid,command.completed_at FROM cmd_ship_crew_payroll_receipt receipt JOIN ship_ship ship USING(ship_id) JOIN cmd_ship_crew_payroll_line line USING(command_id) JOIN cmd_command command USING(command_id) WHERE receipt.campaign_id=%s GROUP BY ship.name,receipt.payroll_day,receipt.total_amount_minor,command.completed_at,receipt.command_id ORDER BY receipt.command_id DESC LIMIT 20""",(campaign_id,)).fetchall()
            route_revenues=connection.execute("""SELECT cycle.public_id::text AS public_id,ship.public_id::text AS ship_public_id,ship.name AS ship_name,origin.name AS origin_name,destination.name AS destination_name,cycle.available_day,max(draw.available_quantity) FILTER(WHERE draw.traffic_kind='freight_tons') AS freight_tons,max(draw.available_quantity) FILTER(WHERE draw.traffic_kind='high_passengers') AS high_passengers,max(draw.available_quantity) FILTER(WHERE draw.traffic_kind='middle_passengers') AS middle_passengers,max(draw.available_quantity) FILTER(WHERE draw.traffic_kind='low_passengers') AS low_passengers FROM cmd_route_revenue_availability_receipt receipt JOIN journey_revenue_availability_cycle cycle USING(revenue_availability_cycle_id) JOIN ship_ship ship USING(ship_id) JOIN loc_location origin ON origin.location_id=cycle.origin_location_id JOIN loc_location destination ON destination.location_id=cycle.destination_location_id JOIN journey_revenue_availability_draw draw USING(revenue_availability_cycle_id) WHERE receipt.campaign_id=%s GROUP BY cycle.public_id,ship.public_id,ship.name,origin.name,destination.name,cycle.available_day,receipt.command_id ORDER BY receipt.command_id DESC LIMIT 20""",(campaign_id,)).fetchall()
            freight_contracts=connection.execute("""SELECT contract.public_id::text AS public_id,ship.name AS ship_name,journey.name AS journey_name,actor.public_id::text AS actor_public_id,contract.accepted_tons,contract.promised_payment_credits,CASE WHEN delivery.freight_contract_id IS NOT NULL THEN 'delivered' WHEN cancellation.freight_contract_id IS NOT NULL THEN 'cancelled' ELSE 'reserved' END AS status FROM journey_freight_contract contract JOIN ship_ship ship USING(ship_id) JOIN journey_journey journey USING(journey_id) JOIN cmd_trading_preparation_receipt setup ON setup.ship_id=ship.ship_id JOIN actor_actor actor ON actor.actor_id=setup.actor_id LEFT JOIN journey_freight_delivery_receipt delivery USING(freight_contract_id) LEFT JOIN journey_freight_cancellation_receipt cancellation USING(freight_contract_id) WHERE contract.campaign_id=%s ORDER BY contract.freight_contract_id DESC""",(campaign_id,)).fetchall()
            passenger_bookings=connection.execute("""SELECT journey.public_id::text AS journey_public_id,journey.name AS journey_name,ship.name AS ship_name,actor.public_id::text AS actor_public_id,receipt.passage_class,receipt.passenger_count,receipt.total_fare_minor,count(*) FILTER(WHERE passage.passage_status='booked') AS awaiting_boarding,count(*) FILTER(WHERE passage.passage_status='boarded') AS boarded FROM cmd_passenger_booking_receipt receipt JOIN journey_journey journey ON journey.journey_id=receipt.journey_id JOIN ship_ship ship ON ship.ship_id=receipt.ship_id JOIN cmd_trading_preparation_receipt setup ON setup.ship_id=ship.ship_id JOIN actor_actor actor ON actor.actor_id=setup.actor_id JOIN cmd_passenger_booking_line line USING(command_id) JOIN journey_passage passage ON passage.journey_passage_id=line.journey_passage_id WHERE receipt.campaign_id=%s GROUP BY journey.public_id,journey.name,ship.name,actor.public_id,receipt.passage_class,receipt.passenger_count,receipt.total_fare_minor,receipt.command_id ORDER BY receipt.command_id DESC""",(campaign_id,)).fetchall()
            low_passengers=connection.execute("SELECT passage.journey_passage_id,actor.name AS passenger_name,journey.name AS journey_name,passage.passage_status FROM journey_passage passage JOIN actor_actor actor ON actor.actor_id=passage.actor_id JOIN journey_journey journey USING(journey_id) WHERE passage.campaign_id=%s AND passage.passage_class='low' ORDER BY passage.journey_passage_id DESC",(campaign_id,)).fetchall()
            passenger_journeys=connection.execute("SELECT journey.public_id::text AS journey_public_id,journey.name AS journey_name,count(*) AS passenger_count,manifest.journey_id IS NOT NULL AS manifest_finalized FROM journey_journey journey JOIN journey_passage passage USING(journey_id,campaign_id) LEFT JOIN journey_passage_manifest_receipt manifest USING(journey_id) WHERE journey.campaign_id=%s AND passage.passage_status IN('booked','boarded') GROUP BY journey.public_id,journey.name,manifest.journey_id ORDER BY journey.name",(campaign_id,)).fetchall()
            postal_contracts=connection.execute("SELECT contract.public_id::text AS public_id,journey.name AS journey_name,ship.name AS ship_name,actor.public_id::text AS actor_public_id,contract.actual_mail_tons,contract.reserved_mail_tons,contract.promised_payment_credits,CASE WHEN delivery.postal_contract_id IS NOT NULL THEN 'delivered' WHEN cancellation.postal_contract_id IS NOT NULL THEN 'cancelled' ELSE 'reserved' END AS status FROM journey_postal_contract contract JOIN journey_journey journey USING(journey_id) JOIN ship_ship ship USING(ship_id) JOIN cmd_trading_preparation_receipt setup ON setup.ship_id=ship.ship_id JOIN actor_actor actor ON actor.actor_id=setup.actor_id LEFT JOIN journey_postal_delivery_receipt delivery USING(postal_contract_id) LEFT JOIN journey_postal_cancellation_receipt cancellation USING(postal_contract_id) WHERE contract.campaign_id=%s ORDER BY contract.postal_contract_id DESC",(campaign_id,)).fetchall()
            charter_quotes=connection.execute("SELECT quote.public_id::text AS public_id,ship.name AS ship_name,quote.billing_blocks,quote.quoted_price_credits,NOT EXISTS(SELECT 1 FROM journey_starship_charter_contract contract WHERE contract.charter_quote_id=quote.charter_quote_id) AS available FROM journey_starship_charter_quote_receipt quote JOIN ship_ship ship USING(ship_id) WHERE quote.campaign_id=%s ORDER BY quote.charter_quote_id DESC",(campaign_id,)).fetchall()
            charter_contracts=connection.execute("SELECT contract.public_id::text AS public_id,journey.name AS journey_name,ship.name AS ship_name,actor.public_id::text AS actor_public_id,contract.promised_payment_credits,completion.charter_contract_id IS NOT NULL AS completed FROM journey_starship_charter_contract contract JOIN journey_journey journey USING(journey_id) JOIN ship_ship ship USING(ship_id) JOIN cmd_trading_preparation_receipt setup ON setup.ship_id=ship.ship_id JOIN actor_actor actor ON actor.actor_id=setup.actor_id LEFT JOIN journey_starship_charter_completion_receipt completion USING(charter_contract_id) WHERE contract.campaign_id=%s ORDER BY contract.charter_contract_id DESC",(campaign_id,)).fetchall()
            mortgages=connection.execute("SELECT ship.public_id::text AS ship_public_id,actor.public_id::text AS actor_public_id,mortgage.cash_price_minor,mortgage.payment_amount_minor,mortgage.payments_made,mortgage.term_months,mortgage.next_due_day,mortgage.mortgage_status,balance.outstanding_minor FROM ship_mortgage mortgage JOIN ship_ship ship USING(ship_id) JOIN cmd_trading_preparation_receipt setup ON setup.ship_id=ship.ship_id JOIN actor_actor actor ON actor.actor_id=setup.actor_id JOIN fin_obligation_balance balance USING(obligation_id) WHERE mortgage.campaign_id=%s ORDER BY mortgage.ship_mortgage_id DESC",(campaign_id,)).fetchall()
            source_documents=connection.execute("SELECT document.public_id::text AS public_id,document.title,document.source_kind,document.original_filename,document.media_type,document.byte_count,document.page_count,document.ingestion_status,intro.introduction_text,count(*) FILTER(WHERE page.review_status='verified') AS verified_pages,count(*) FILTER(WHERE page.visual_review_required) AS visual_review_pages FROM camp_source_document document JOIN camp_source_page page USING(source_document_id,campaign_id) LEFT JOIN camp_source_player_intro intro USING(source_document_id,campaign_id) WHERE document.campaign_id=%s GROUP BY document.source_document_id,intro.introduction_text ORDER BY document.uploaded_at DESC",(campaign_id,)).fetchall()
            referee_messages=connection.execute("SELECT message.speaker_kind,message.message_text,message.created_at FROM camp_referee_message message JOIN camp_referee_turn turn USING(referee_turn_id,campaign_id) WHERE message.campaign_id=%s AND turn.turn_status='completed' ORDER BY message.referee_message_id DESC LIMIT 40",(campaign_id,)).fetchall()[::-1]
            referee_tool_requests=connection.execute("SELECT request.public_id::text AS public_id,request.tool_name,request.request_summary FROM camp_referee_tool_request request WHERE request.campaign_id=%s AND request.request_status='proposed' ORDER BY request.referee_tool_request_id",(campaign_id,)).fetchall()
            encounters=connection.execute("""SELECT encounter.public_id::text AS public_id,type.encounter_type_code,encounter.encounter_status,encounter.current_mode,combat.current_round,combat.combat_status,count(participant.actor_id) AS participant_count,COALESCE(array_agg(actor.name ORDER BY actor.name) FILTER(WHERE actor.actor_id IS NOT NULL),ARRAY[]::text[]) AS participant_names,COALESCE(array_agg(actor.public_id::text ORDER BY actor.name) FILTER(WHERE actor.actor_id IS NOT NULL),ARRAY[]::text[]) AS participant_public_ids FROM enc_encounter encounter JOIN rule_encounter_type type ON type.rule_id=encounter.encounter_type_rule_id LEFT JOIN enc_participant participant USING(encounter_id) LEFT JOIN actor_actor actor USING(actor_id) LEFT JOIN enc_personal_combat combat USING(encounter_id) WHERE encounter.campaign_id=%s GROUP BY encounter.encounter_id,type.encounter_type_code,combat.current_round,combat.combat_status ORDER BY encounter.created_at DESC""",(campaign_id,)).fetchall()
            weapon_options=connection.execute("""SELECT weapon.rule_code AS weapon_rule_code,weapon.name AS weapon_name,mode.attack_profile_code,range_rule.rule_code AS range_rule_code,replace(range_rule.rule_code,'combat.range.','') AS range_name FROM inv_weapon_attack_mode mode JOIN rule_rule weapon ON weapon.rule_id=mode.item_rule_id JOIN combat_attack_profile_difficulty difficulty ON difficulty.attack_profile_code=mode.attack_profile_code AND difficulty.permitted JOIN rule_rule range_rule ON range_rule.rule_id=difficulty.range_band_rule_id ORDER BY weapon.name,mode.display_order,range_rule.rule_code""").fetchall()
            armor_options=connection.execute("SELECT armor.rule_code AS armor_rule_code,armor.name AS armor_name FROM inv_armor_definition definition JOIN rule_rule armor ON armor.rule_id=definition.item_rule_id ORDER BY armor.name").fetchall()
            for encounter in encounters:
                encounter["combatants"]=connection.execute("""SELECT actor.public_id::text AS actor_public_id,actor.name,combatant.initiative_current,combatant.significant_actions_remaining,combatant.minor_actions_remaining,combatant.turn_started_this_round,combatant.acted_this_round,combatant.delayed_this_round,combatant.metres_moved_this_round,stance.stance_code,COALESCE(injury.injury_status,'uninjured') AS injury_status,physical.strength,physical.dexterity,physical.endurance FROM enc_personal_combatant combatant JOIN enc_encounter encounter USING(encounter_id) JOIN actor_actor actor USING(actor_id) JOIN rule_personal_stance stance ON stance.rule_id=combatant.stance_rule_id LEFT JOIN health_actor_injury_status injury USING(actor_id) LEFT JOIN LATERAL (SELECT max(characteristic.current_value) FILTER(WHERE rule.rule_code='characteristic.strength') AS strength,max(characteristic.current_value) FILTER(WHERE rule.rule_code='characteristic.dexterity') AS dexterity,max(characteristic.current_value) FILTER(WHERE rule.rule_code='characteristic.endurance') AS endurance FROM actor_characteristic characteristic JOIN rule_rule rule ON rule.rule_id=characteristic.characteristic_rule_id WHERE characteristic.actor_id=actor.actor_id) physical ON true WHERE encounter.public_id=%s ORDER BY combatant.initiative_current DESC,combatant.dexterity_value DESC,actor.actor_id""",(encounter["public_id"],)).fetchall()
                awaiting=[row for row in encounter["combatants"] if not row["acted_this_round"] and not row["delayed_this_round"]]
                encounter["next_actor_public_id"]=awaiting[0]["actor_public_id"] if awaiting else None
                encounter["round_complete"]=bool(encounter["combatants"]) and all(row["acted_this_round"] for row in encounter["combatants"])
                encounter["pending_attacks"]=connection.execute("""SELECT attack.public_id::text AS public_id,attacker.public_id::text AS attacker_public_id,attacker.name AS attacker_name,target.public_id::text AS target_public_id,target.name AS target_name,weapon.rule_code AS weapon_rule_code,weapon.name AS weapon_name,attack.attack_profile_code,range_rule.rule_code AS range_rule_code,attack.target_has_cover,target_state.turn_started_this_round,EXISTS(SELECT 1 FROM cmd_personal_reaction_receipt reaction WHERE reaction.personal_attack_id=attack.personal_attack_id) AS reaction_declared FROM enc_personal_attack attack JOIN enc_encounter encounter USING(encounter_id) JOIN actor_actor attacker ON attacker.actor_id=attack.attacker_actor_id JOIN actor_actor target ON target.actor_id=attack.target_actor_id JOIN enc_personal_combatant target_state ON target_state.encounter_id=attack.encounter_id AND target_state.actor_id=attack.target_actor_id JOIN rule_rule weapon ON weapon.rule_id=attack.weapon_rule_id JOIN rule_rule range_rule ON range_rule.rule_id=attack.range_band_rule_id WHERE encounter.public_id=%s AND attack.attack_status='awaiting_reactions' ORDER BY attack.personal_attack_id""",(encounter["public_id"],)).fetchall()
                encounter["sides"]=connection.execute("SELECT side_code,side_name FROM enc_side side JOIN enc_encounter encounter USING(encounter_id) WHERE encounter.public_id=%s ORDER BY side.display_order",(encounter["public_id"],)).fetchall()
        return {
            **campaign,
            "actors": actors,
            "ships": ships,
            "crew_positions": crew_positions,
            "systems": systems,
            "journeys": journeys,
            "markets": markets,
            "broker_quotes": broker_quotes,
            "trading_accounts": trading_accounts,
            "purchases": purchases,
            "cargo_lots": cargo_lots,
            "sale_quotes": sale_quotes,
            "sales": sales,
            "refuelings": refuelings,
            "ship_expenses": ship_expenses,
            "journal_notes": journal_notes,
            "session_archives": session_archives,
            "crew_payrolls": crew_payrolls,
            "route_revenues": route_revenues,
            "freight_contracts": freight_contracts,
            "passenger_bookings": passenger_bookings,
            "low_passengers": low_passengers,
            "passenger_journeys": passenger_journeys,
            "postal_contracts": postal_contracts,
            "charter_quotes": charter_quotes,
            "charter_contracts": charter_contracts,
            "mortgages": mortgages,
            "source_documents": source_documents,
            "referee_messages": referee_messages,
            "referee_tool_requests": referee_tool_requests,
            "encounters": encounters,
            "weapon_options": weapon_options,
            "armor_options": armor_options,
        }

    def ship_classes(self) -> list[dict[str, Any]]:
        if not self.url: return []
        with self._connect() as connection:
            return connection.execute(
                "SELECT class_code,hull_tons,minimum_tech_level,jump_rating,maneuver_rating,cargo_capacity_tons FROM ship_class ORDER BY hull_tons,class_code"
            ).fetchall()

    def status(self) -> dict[str, Any]:
        if not self.url:
            return {"configured": False, "connected": False}
        try:
            with self._connect() as connection:
                version = connection.execute(
                    "SELECT COALESCE(max(migration_number),0) AS version "
                    "FROM sys_schema_migration"
                ).fetchone()["version"]
            return {"configured": True, "connected": True, "schema_version": version}
        except psycopg.Error as exc:
            return {
                "configured": True,
                "connected": False,
                "error": exc.__class__.__name__,
            }


def summary_dict(summary: CampaignSummary) -> dict[str, Any]:
    return asdict(summary)
