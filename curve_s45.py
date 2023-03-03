from dataclasses import dataclass, field

import QuantLib as ql
from blp import blp


@dataclass
class Quotes:
    quotes: dict[str, ql.SimpleQuote] = field(
        init=False, repr=False, default_factory=dict
    )

    def get(self, ticker: str) -> ql.SimpleQuote:
        if ticker not in self.quotes:
            self.quotes[ticker] = ql.SimpleQuote(0.0)
        return self.quotes[ticker]

    def update(self) -> None:
        with blp.BlpQuery() as bq:
            data = bq.bdp([ticker for ticker in self.quotes.keys()], ["px_last"])

        for _, row in data.iterrows():
            ticker = row["security"]
            level = row["px_last"]
            self.quotes[ticker].setValue(level)


def build_curve(quotes: Quotes) -> tuple[ql.PiecewiseLogCubicDiscount, ql.IborIndex]:
    index_ticker = "EUR006M Index"
    curve_id = "S45"
    discount_curve_id = "S514"
    calendar = ql.TARGET()
    this_curve_handle = ql.RelinkableYieldTermStructureHandle()
    index = ql.IborIndex(
        "Euribor6M",
        ql.Period("6M"),
        2,
        ql.EURCurrency(),
        calendar,
        ql.ModifiedFollowing,
        False,
        ql.Actual360(),
        this_curve_handle,
    )
    fixed_frequency = ql.Annual
    fixed_convention = ql.ModifiedFollowing
    fixed_day_counter = ql.Thirty360(ql.Thirty360.USA)
    helpers = (
        [
            ql.DepositRateHelper(
                ql.QuoteHandle(
                    ql.DerivedQuote(
                        ql.QuoteHandle(quotes.get(index_ticker)), lambda x: x / 100
                    )
                ),
                index,
            )
        ]
        + [
            ql.FraRateHelper(
                ql.QuoteHandle(
                    ql.DerivedQuote(
                        ql.QuoteHandle(quotes.get(ticker)), lambda x: x / 100
                    )
                ),
                months_to_start,
                index,
            )
            for months_to_start, ticker in [
                (1, "EUFR0AG BGN Curncy"),
                (2, "EUFR0BH BGN Curncy"),
                (3, "EUFR0CI BGN Curncy"),
                (4, "EUFR0DJ BGN Curncy"),
                (5, "EUFR0EK BGN Curncy"),
                (6, "EUFR0F1 BGN Curncy"),
                (9, "EUFR0I1C BGN Curncy"),
                (12, "EUFR011F BGN Curncy"),
            ]
        ]
        + [
            ql.SwapRateHelper(
                ql.QuoteHandle(
                    ql.DerivedQuote(
                        ql.QuoteHandle(quotes.get(ticker)), lambda x: x / 100
                    )
                ),
                ql.Period(tenor),
                calendar,
                fixed_frequency,
                fixed_convention,
                fixed_day_counter,
                index,
                ql.QuoteHandle(ql.SimpleQuote(0.0)),
                ql.Period(),
            )
            for tenor, ticker in [
                ("2Y", "EUSA2 BGN Curncy"),
                ("3Y", "EUSA3 BGN Curncy"),
                ("4Y", "EUSA4 BGN Curncy"),
                ("5Y", "EUSA5 BGN Curncy"),
                ("6Y", "EUSA6 BGN Curncy"),
                ("7Y", "EUSA7 BGN Curncy"),
                ("8Y", "EUSA8 BGN Curncy"),
                ("9Y", "EUSA9 BGN Curncy"),
                ("10Y", "EUSA10 BGN Curncy"),
                ("11Y", "EUSA11 BGN Curncy"),
                ("12Y", "EUSA12 BGN Curncy"),
                ("15Y", "EUSA15 BGN Curncy"),
                ("20Y", "EUSA20 BGN Curncy"),
                ("25Y", "EUSA25 BGN Curncy"),
                ("30Y", "EUSA30 BGN Curncy"),
                ("40Y", "EUSA40 BGN Curncy"),
                # ("50Y", "EUSA50 BGN Curncy"),
            ]
        ]
    )
    curve = ql.PiecewiseLogCubicDiscount(2, calendar, helpers, ql.Actual360())
    return curve, index


def main():
    quotes = Quotes()
    curve, index = build_curve(quotes)
    quotes.update()

    for date in curve.dates():
        print(date, curve.zeroRate(date, ql.Actual365Fixed(), ql.Continuous))


if __name__ == "__main__":
    main()
