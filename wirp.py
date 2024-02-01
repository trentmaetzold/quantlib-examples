from dataclasses import dataclass, field

import pandas as pd
import QuantLib as ql
from blp import blp


@dataclass
class Quotes:
    _data: dict[str, ql.SimpleQuote] = field(init=False, default_factory=dict)

    def get(self, ticker: str) -> ql.SimpleQuote:
        if ticker not in self._data:
            self._data[ticker] = ql.SimpleQuote(0.0)

        return self._data[ticker]

    def set(self, ticker: str, value: float) -> None:
        self.get(ticker).setValue(value)

    def update(self) -> None:
        with blp.BlpQuery() as bq:
            data = bq.bdp(list(self._data.keys()), ["px_last"])

        for _, row in data.iterrows():
            self.set(row["security"], row["px_last"])


quotes = Quotes()


@dataclass
class Calendars:
    _data: dict[str, ql.Calendar] = field(init=False, default_factory=dict)

    def get(self, id: str) -> ql.Calendar:
        if id not in self._data:
            calendar = ql.BespokeCalendar(id)

            with blp.BlpQuery() as bq:
                data = bq.bds(
                    ["GT10 Govt"],
                    "CALENDAR_HOLIDAYS",
                    overrides=[("SETTLEMENT_CALENDAR_CODE", id)],
                )

            for weekend in [1, 7]:
                calendar.addWeekend(weekend)

            for date in data["Holiday Date"]:
                calendar.addHoliday(ql.Date.from_date(date))

            self._data[id] = calendar

        return self._data[id]


calendars = Calendars()


@dataclass
class Curve:
    handle: ql.RelinkableYieldTermStructureHandle
    disc_handle: ql.RelinkableYieldTermStructureHandle
    index: ql.OvernightIndex
    helpers: list[ql.OISRateHelper]
    curve: ql.PiecewiseLogCubicDiscount


def build_sofr() -> "Curve":
    tickers = [
        ("1W", "USOSFR1Z Curncy"),
        ("2W", "USOSFR2Z Curncy"),
        ("3W", "USOSFR3Z Curncy"),
        ("1M", "USOSFRA Curncy"),
        ("2M", "USOSFRB Curncy"),
        ("3M", "USOSFRC Curncy"),
        ("4M", "USOSFRD Curncy"),
        ("5M", "USOSFRE Curncy"),
        ("6M", "USOSFRF Curncy"),
        ("7M", "USOSFRG Curncy"),
        ("8M", "USOSFRH Curncy"),
        ("9M", "USOSFRI Curncy"),
        ("10M", "USOSFRJ Curncy"),
        ("11M", "USOSFRK Curncy"),
        ("12M", "USOSFR1 Curncy"),
        ("18M", "USOSFR1F Curncy"),
        ("2Y", "USOSFR2 Curncy"),
        ("3Y", "USOSFR3 Curncy"),
        ("4Y", "USOSFR4 Curncy"),
        ("5Y", "USOSFR5 Curncy"),
        ("6Y", "USOSFR6 Curncy"),
        ("7Y", "USOSFR7 Curncy"),
        ("8Y", "USOSFR8 Curncy"),
        ("9Y", "USOSFR9 Curncy"),
        ("10Y", "USOSFR10 Curncy"),
        ("12Y", "USOSFR12 Curncy"),
        ("15Y", "USOSFR15 Curncy"),
        ("20Y", "USOSFR20 Curncy"),
        ("25Y", "USOSFR25 Curncy"),
        ("30Y", "USOSFR30 Curncy"),
        ("40Y", "USOSFR40 Curncy"),
        ("50Y", "USOSFR50 Curncy"),
    ]
    handle = ql.RelinkableYieldTermStructureHandle()
    index = ql.OvernightIndex(
        "SOFR", 0, ql.USDCurrency(), calendars.get("GT"), ql.Actual360(), handle
    )
    helpers = [
        ql.OISRateHelper(
            2,  # settlementDays
            ql.Period(tenor),
            ql.QuoteHandle(
                ql.DerivedQuote(ql.QuoteHandle(quotes.get(ticker)), lambda x: x / 100)
            ),
            index,
            handle,  # discountingCurve
            False,  # telescopicValueDates
            2,  # paymentLag
            ql.ModifiedFollowing,
            ql.Annual,
            calendars.get("FD"),
            ql.Period("0D"),  # forwardStart
            0.0,  # overnightSpread
            ql.Pillar.MaturityDate,
            ql.Date(),  # customPillarDate
            ql.RateAveraging.Compound,
            True,  # endOfMonth
        )
        for tenor, ticker in tickers
    ]
    curve = ql.PiecewiseLogCubicDiscount(
        0, calendars.get("FD"), helpers, ql.Actual360()
    )
    handle.linkTo(curve)

    return Curve(handle, handle, index, helpers, curve)


def build_fed_funds(sofr_handle: ql.RelinkableYieldTermStructureHandle) -> "Curve":
    tickers = [
        ("1W", "USSO1Z Curncy"),
        ("2W", "USSO2Z Curncy"),
        ("3W", "USSO3Z Curncy"),
        ("1M", "USSOA Curncy"),
        ("2M", "USSOB Curncy"),
        ("3M", "USSOC Curncy"),
        ("4M", "USSOD Curncy"),
        ("5M", "USSOE Curncy"),
        ("6M", "USSOF Curncy"),
        ("9M", "USSOI Curncy"),
        ("12M", "USSO1 Curncy"),
        ("18M", "USSO1F Curncy"),
    ]
    handle = ql.RelinkableYieldTermStructureHandle()
    index = ql.OvernightIndex(
        "Fed Funds", 0, ql.USDCurrency(), calendars.get("FD"), ql.Actual360(), handle
    )
    helpers = [
        ql.OISRateHelper(
            2,  # settlementDays
            ql.Period(tenor),
            ql.QuoteHandle(
                ql.DerivedQuote(ql.QuoteHandle(quotes.get(ticker)), lambda x: x / 100)
            ),
            index,
            sofr_handle,  # discountingCurve
            False,  # telescopicValueDates
            2,  # paymentLag
            ql.ModifiedFollowing,
            ql.Annual,
            calendars.get("FD"),
            ql.Period("0D"),  # forwardStart
            0.0,  # overnightSpread
            ql.Pillar.MaturityDate,
            ql.Date(),  # customPillarDate
            ql.RateAveraging.Compound,
            True,  # endOfMonth
        )
        for tenor, ticker in tickers
    ]
    curve = ql.PiecewiseLogCubicDiscount(
        0, calendars.get("FD"), helpers, ql.Actual360()
    )
    handle.linkTo(curve)

    return Curve(handle, sofr_handle, index, helpers, curve)


def make_fed_funds_swap(
    index: ql.OvernightIndex,
    effective_date: ql.Date,
    maturity_date: ql.Date,
    sofr_handle: ql.RelinkableYieldTermStructureHandle,
) -> ql.OvernightIndexedSwap:
    return ql.MakeOIS(
        swapTenor=ql.Period("1D"),
        overnightIndex=index,
        fixedRate=0.05,
        effectiveDate=effective_date,
        terminationDate=maturity_date,
        dateGenerationRule=ql.DateGeneration.Backward,
        paymentFrequency=ql.Annual,
        paymentAdjustmentConvention=ql.ModifiedFollowing,
        paymentLag=2,
        paymentCalendar=calendars.get("FD"),
        fixedLegDayCount=ql.Actual360(),
        discountingTermStructure=sofr_handle,
        telescopicValueDates=False,
    )


def get_compound_factor(
    rate: float, effective_date: ql.Date, maturity_date: ql.Date, calendar: ql.Calendar
) -> float:
    dates = calendar.businessDayList(effective_date, maturity_date - 1) + (
        maturity_date,
    )
    result = 1

    for d1, d2 in zip(dates[:-1], dates[1:]):
        result *= 1 + rate * (d2 - d1) / 360

    return result


def get_implied_rate(
    curve: "Curve",
    prior_implied_rate: float,
    effective_date: ql.Date,
    maturity_date: ql.Date,
    calendar: ql.Calendar,
    tgt_compound_factor: float | None = None,
    precision: float = 1e-7,
    h: float = 1e-6,
) -> float:
    if tgt_compound_factor is None:
        swap = make_fed_funds_swap(
            curve.index, effective_date, maturity_date, curve.disc_handle
        )
        swap_rate = swap.fairRate()
        tgt_compound_factor = 1 + swap_rate * (maturity_date - effective_date) / 360

    guess = prior_implied_rate
    guess_compound_factor = get_compound_factor(
        guess, effective_date, maturity_date, calendar
    )

    while abs(guess_compound_factor - tgt_compound_factor) > precision:
        f_x = guess_compound_factor - tgt_compound_factor
        dx_dy = (
            get_compound_factor(guess + h, effective_date, maturity_date, calendar)
            - get_compound_factor(guess - h, effective_date, maturity_date, calendar)
        ) / (2 * h)
        guess = guess - f_x / dx_dy
        guess_compound_factor = get_compound_factor(
            guess, effective_date, maturity_date, calendar
        )

    return guess

def get_cur_implied_on_ticker(policy_dates: list[ql.Date]):
    calendar= calendars.get("FD")
    spot_date = calendar.advance(ql.Date.todaysDate(), 2, ql.Days)
    first_policy_date = [date for date in policy_dates if date > spot_date][0]
    preferred_tickers = [
            ("1W", "USSO1Z Curncy"),
            ("2W", "USSO2Z Curncy"),
            ("3W", "USSO3Z Curncy"),
            ("1M", "USSOA Curncy"),
            ("2M", "USSOB Curncy"),
            ("3M", "USSOC Curncy"),
            ("4M", "USSOD Curncy"),
            ("5M", "USSOE Curncy"),
            ("6M", "USSOF Curncy"),
            ("9M", "USSOI Curncy"),
            ("12M", "USSO1 Curncy"),
            ("18M", "USSO1F Curncy"),
        ]
    
    for tenor, ticker in preferred_tickers:
        if first_policy_date >= calendar.advance(spot_date, ql.Period(tenor)):
            return tenor, ticker
    
    return None


policy_dates = [
    # ql.Date(31, 1, 2024),
    ql.Date(20, 3, 2024),
    ql.Date(1, 5, 2024),
    ql.Date(12, 6, 2024),
    ql.Date(31, 7, 2024),
    ql.Date(18, 9, 2024),
    ql.Date(7, 11, 2024),
    ql.Date(18, 12, 2024),
    ql.Date(29, 1, 2025),
    ql.Date(2, 2, 2025),
]

sofr = build_sofr()
fed_funds = build_fed_funds(sofr.handle)
index_quote = quotes.get("FEDL01 Index")
quotes.update()

cur_implied_on_rate = index_quote.value() if (res := get_cur_implied_on_ticker(policy_dates)) is None else res
print(cur_implied_on_rate)
print(
    ql.Date(2, 2, 2024),
    ql.Date(2, 3, 2024),
    get_implied_rate(
        fed_funds,
        index_quote.value(),
        ql.Date(2, 2, 2024),
        ql.Date(2, 3, 2024),
        calendars.get("FD"),
    ),
)

for effective_date, maturity_date in zip(policy_dates[:-1], policy_dates[1:]):
    print(
        effective_date,
        maturity_date,
        get_implied_rate(
            fed_funds,
            index_quote.value(),
            effective_date,
            maturity_date,
            calendars.get("FD"),
        ),
    )

for helper in fed_funds.helpers:
    print(
        helper.earliestDate(),
        helper.latestDate(),
        get_implied_rate(
            fed_funds,
            index_quote.value(),
            helper.earliestDate(),
            helper.latestDate(),
            calendars.get("FD"),
        ),
    )
