import asyncio
from datetime import datetime, timedelta


class Details:
    def __init__(self, tr, isin):
        self.tr = tr
        self.isin = isin

    async def details_loop(self):
        asyncio.create_task(self.tr.recv2())
        (
            self.stockDetails,
            self.neonNews,
            self.performance,
            self.instrument,
            self.instrumentSuitability,
        ) = await asyncio.gather(
            (await self.tr.stock_details2(self.isin)).get(),
            (await self.tr.news2(self.isin)).get(),
            (await self.tr.performance2(self.isin, exchange="LSX")).get(),
            (await self.tr.instrument_details2(self.isin)).get(),
            (await self.tr.instrument_suitability2(self.isin)).get(),
        )

    def print_instrument(self):
        print("Name:", self.instrument["name"])
        print("ShortName:", self.instrument["shortName"])
        print("Type:", self.instrument["typeId"])
        for ex in self.instrument["exchanges"]:
            print(f"{ex['slug']}: {ex['symbolAtExchange']} {ex['nameAtExchange']}")

        for tag in self.instrument["tags"]:
            print(f"{tag['type']}: {tag['name']}")

    def stock_details(self):
        company = self.stockDetails["company"]
        for company_detail in company:
            if company[company_detail] is not None:
                print(f"{company_detail:15}: {company[company_detail]}")
        for detail in self.stockDetails:
            if detail != "company" and self.stockDetails[detail] is not None and self.stockDetails[detail] != []:
                print(f"{detail:15}: {self.stockDetails[detail]}")

    def news(self, relevant_days=30):
        since = datetime.now() - timedelta(days=relevant_days)
        if not hasattr(self, "neonNews"):
            return
        for news in self.neonNews:
            newsdate = datetime.fromtimestamp(news["createdAt"] / 1000.0)
            if newsdate > since:
                dateiso = newsdate.isoformat(sep=" ", timespec="minutes")
                print(f"{dateiso}: {news['headline']}")

    def overview(self):
        self.print_instrument()
        self.news()
        self.stock_details()

    def get(self):
        asyncio.get_event_loop().run_until_complete(self.details_loop())

        self.overview()
