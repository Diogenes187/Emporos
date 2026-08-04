import os
import unittest
import uuid

import psycopg

from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command
from engine.commerce_setup import prepare_trading_command
from engine.passenger_boarding import board_route_passengers_command
from engine.passenger_booking import book_route_passengers_command
from engine.passenger_manifest import finalize_passenger_manifest_command
from engine.route_revenue import open_route_revenue_command
from engine.sectors import import_sector_command
from engine.ships import acquire_ship_command
from engine.travel_planning import place_ship_command, plan_jump_journey_command


class Fixed:
    def randint(self, low, high):
        return min(3, high)


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL"
)
class PassengerDepartureTests(unittest.TestCase):
    def test_low_passengers_can_be_manifested_and_boarded(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                suffix = str(uuid.uuid4())
                owner = "passenger-departure-test"
                campaign = create_campaign_command(
                    connection,
                    initiator_reference=owner,
                    idempotency_key="campaign-" + suffix,
                    name="Passenger departure",
                )
                actor = initialize_character_command(
                    connection,
                    initiator_reference=owner,
                    idempotency_key="actor-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    character_name="Master",
                    random_source=Fixed(),
                )
                ship = acquire_ship_command(
                    connection,
                    initiator_reference=owner,
                    idempotency_key="ship-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    owner_actor_public_id=actor.actor_public_id,
                    class_code="merchant-trader",
                    ship_name="Passage",
                )
                prepare_trading_command(
                    connection,
                    initiator_reference=owner,
                    idempotency_key="setup-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    actor_public_id=actor.actor_public_id,
                    ship_public_id=ship.ship_public_id,
                    opening_balance=0,
                )
                import_sector_command(
                    connection,
                    initiator_reference=owner,
                    idempotency_key="sector-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    sector_name="Test",
                    sector_x=0,
                    sector_y=0,
                    source_filename="passage.tab",
                    content=b"Name\tHex\tUWP\nAlpha\t0101\tA788899-C\nBeta\t0201\tB788899-C\n",
                )
                systems = connection.execute(
                    """SELECT location.public_id
                       FROM loc_star_system system
                       JOIN loc_location location ON location.location_id=system.location_id
                       WHERE system.campaign_id=(SELECT campaign_id FROM camp_campaign WHERE public_id=%s)
                       ORDER BY system.hex_column""",
                    (campaign.campaign_public_id,),
                ).fetchall()
                place_ship_command(
                    connection,
                    initiator_reference=owner,
                    idempotency_key="place-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    ship_public_id=ship.ship_public_id,
                    system_public_id=systems[0][0],
                )
                route = open_route_revenue_command(
                    connection,
                    initiator_reference=owner,
                    idempotency_key="route-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    ship_public_id=ship.ship_public_id,
                    destination_system_public_id=systems[1][0],
                    random_source=Fixed(),
                )
                journey = plan_jump_journey_command(
                    connection,
                    initiator_reference=owner,
                    idempotency_key="journey-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    ship_public_id=ship.ship_public_id,
                    destination_system_public_id=systems[1][0],
                    journey_name="Low passage run",
                )
                book_route_passengers_command(
                    connection,
                    initiator_reference=owner,
                    idempotency_key="booking-" + suffix,
                    cycle_public_id=route.cycle_public_id,
                    journey_public_id=journey.journey_public_id,
                    passage_class="low",
                    passenger_count=2,
                    random_source=Fixed(),
                )
                manifest = finalize_passenger_manifest_command(
                    connection,
                    initiator_reference=owner,
                    idempotency_key="manifest-" + suffix,
                    journey_public_id=journey.journey_public_id,
                )
                boarding = board_route_passengers_command(
                    connection,
                    initiator_reference=owner,
                    idempotency_key="boarding-" + suffix,
                    journey_public_id=journey.journey_public_id,
                    actor_public_id=actor.actor_public_id,
                )
                self.assertEqual(manifest.low_berths, 2)
                self.assertEqual(boarding.passenger_count, 2)
                self.assertEqual(boarding.total_fare, 2000)
                self.assertEqual(boarding.balance_after, 2000)
                positioned = connection.execute(
                    """SELECT count(*)
                       FROM journey_participant participant
                       JOIN loc_actor_position position
                         ON position.actor_id=participant.actor_id
                        AND position.position_status='current'
                       WHERE participant.journey_id=(SELECT journey_id FROM journey_journey WHERE public_id=%s)
                         AND participant.participant_role='passenger'""",
                    (journey.journey_public_id,),
                ).fetchone()[0]
                self.assertEqual(positioned, 2)


if __name__ == "__main__":
    unittest.main()
