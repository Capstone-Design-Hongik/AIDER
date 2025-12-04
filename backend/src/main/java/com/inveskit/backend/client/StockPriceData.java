package com.inveskit.backend.client;

import lombok.Builder;
import lombok.Getter;

import java.math.BigDecimal;
import java.time.LocalDate;

@Getter
@Builder
public class StockPriceData {
    private LocalDate date;
    private BigDecimal closePrice;
}
