"""Create database schema and seed sample listings for development."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

from sqlalchemy import delete

from app.db.session import SessionLocal, engine
from app.models.availability import Availability, AvailabilityStatus
from app.models.base import Base
from app.models.lead import Lead, LeadStage
from app.models.property import Property
from app.models.unit import Unit

PROPERTIES = [
	{
		"id": "prop-park-vista",
		"name": "Park Vista Residences",
		"address": "92 Clifton Block 5",
		"city": "Karachi",
		"policies": {
			"fees": [
				{"name": "application", "amount": 2500},
				{"name": "security", "amount": 15000},
			],
			"utilities_included": ["water", "trash"],
			"notes": "Families preferred. No pets larger than 15kg.",
		},
		"units": [
			{
				"id": "unit-park-201",
				"title": "2BR Park View with Balcony",
				"beds": 2,
				"baths": 2,
				"sqft": 980,
				"rent": 120_000,
				"deposit": 240_000,
				"furnished": False,
				"amenities": ["parking", "generator", "gym"],
				"images": ["https://picsum.photos/seed/park201/800/600"],
				"available_from": date(2025, 10, 12),
				"availability": [
					date(2025, 10, 13),
					date(2025, 10, 14),
					date(2025, 10, 16),
				],
			},
			{
				"id": "unit-park-1703",
				"title": "3BR Corner Penthouse",
				"beds": 3,
				"baths": 3,
				"sqft": 1520,
				"rent": 195_000,
				"deposit": 390_000,
				"furnished": True,
				"amenities": ["parking", "smart_home", "concierge"],
				"images": ["https://picsum.photos/seed/park1703/800/600"],
				"available_from": date(2025, 10, 25),
				"availability": [
					date(2025, 10, 26),
					date(2025, 10, 27),
					date(2025, 10, 30),
				],
			},
		],
	},
	{
		"id": "prop-seaview-lofts",
		"name": "Seaview Lofts",
		"address": "18 Do Talwar",
		"city": "Karachi",
		"policies": {
			"fees": [
				{"name": "service", "amount": 6000},
			],
			"utilities_included": ["water"],
			"notes": "Pets allowed with additional deposit.",
		},
		"units": [
			{
				"id": "unit-loft-504",
				"title": "1BR Furnished Loft",
				"beds": 1,
				"baths": 1,
				"sqft": 720,
				"rent": 85_000,
				"deposit": 170_000,
				"furnished": True,
				"amenities": ["sea_view", "parking", "roof_top"],
				"images": ["https://picsum.photos/seed/loft504/800/600"],
				"available_from": date(2025, 10, 18),
				"availability": [
					date(2025, 10, 18),
					date(2025, 10, 19),
					date(2025, 10, 22),
				],
			},
			{
				"id": "unit-loft-1002",
				"title": "Studio City View",
				"beds": 0,
				"baths": 1,
				"sqft": 520,
				"rent": 62_000,
				"deposit": 124_000,
				"furnished": False,
				"amenities": ["generator", "parking"],
				"images": ["https://picsum.photos/seed/loft1002/800/600"],
				"available_from": date(2025, 10, 5),
				"availability": [
					date(2025, 10, 12),
					date(2025, 10, 13),
					date(2025, 10, 15),
				],
			},
		],
	},
]


LEADS = [
	{
		"id": "lead-ava",
		"name": "Ava Khan",
		"phone": "+92-300-5551234",
		"email": "ava.khan@example.com",
		"stage": LeadStage.ENGAGED,
	},
	{
		"id": "lead-daniel",
		"name": "Daniel Lee",
		"phone": "+92-311-9876543",
		"email": "daniel.lee@example.com",
		"stage": LeadStage.NEW,
	},
	{
		"id": "lead-sofia",
		"name": "Sofia Rehman",
		"phone": "+92-321-1119090",
		"email": "sofia.rehman@example.com",
		"stage": LeadStage.BOOKED,
	},
]


async def create_schema() -> None:
	"""Create the database schema if it does not already exist."""

	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)


async def seed_properties() -> None:
	"""Insert or update demo properties, units, and availability."""

	async with SessionLocal() as session:
		async with session.begin():
			for prop in PROPERTIES:
				property_obj = await session.get(Property, prop["id"])
				if property_obj is None:
					property_obj = Property(
						id=prop["id"],
						name=prop["name"],
						address=prop["address"],
						city=prop["city"],
						policies_json=prop["policies"],
					)
					session.add(property_obj)
				else:
					property_obj.name = prop["name"]
					property_obj.address = prop["address"]
					property_obj.city = prop["city"]
					property_obj.policies_json = prop["policies"]

				for unit_data in prop["units"]:
					unit_obj = await session.get(Unit, unit_data["id"])
					if unit_obj is None:
						unit_obj = Unit(
							id=unit_data["id"],
							property_id=prop["id"],
							title=unit_data["title"],
							beds=unit_data["beds"],
							baths=unit_data["baths"],
							sqft=unit_data["sqft"],
							rent=unit_data["rent"],
							deposit=unit_data["deposit"],
							furnished=unit_data["furnished"],
							amenities=unit_data["amenities"],
							available_from=unit_data["available_from"],
							images=unit_data["images"],
						)
						session.add(unit_obj)
					else:
						unit_obj.property_id = prop["id"]
						unit_obj.title = unit_data["title"]
						unit_obj.beds = unit_data["beds"]
						unit_obj.baths = unit_data["baths"]
						unit_obj.sqft = unit_data["sqft"]
						unit_obj.rent = unit_data["rent"]
						unit_obj.deposit = unit_data["deposit"]
						unit_obj.furnished = unit_data["furnished"]
						unit_obj.amenities = unit_data["amenities"]
						unit_obj.available_from = unit_data["available_from"]
						unit_obj.images = unit_data["images"]

					await session.execute(
						delete(Availability).where(Availability.unit_id == unit_data["id"])
					)

					for day in unit_data["availability"]:
						session.add(
							Availability(
								unit_id=unit_data["id"],
								date_from=day,
								status=AvailabilityStatus.AVAILABLE,
							)
						)

async def seed_leads() -> None:
	"""Insert demo leads for development flows."""

	async with SessionLocal() as session:
		async with session.begin():
			for lead_data in LEADS:
				lead = await session.get(Lead, lead_data["id"])
				if lead is None:
					lead = Lead(
						id=lead_data["id"],
						name=lead_data["name"],
						phone=lead_data["phone"],
						email=lead_data["email"],
						source="seed",
						stage=lead_data["stage"],
						created_at=datetime.now(timezone.utc),
					)
					session.add(lead)
				else:
					lead.name = lead_data["name"]
					lead.phone = lead_data["phone"]
					lead.email = lead_data["email"]
					lead.stage = lead_data["stage"]
					lead.source = "seed"
					if lead.created_at is None:
						lead.created_at = datetime.now(timezone.utc)
					session.add(lead)


async def main() -> None:
	await create_schema()
	await seed_properties()
	await seed_leads()
	print("Database schema ensured and demo data seeded.")


if __name__ == "__main__":
	asyncio.run(main())
