package com.inveskit.backend.dto;


import lombok.Builder;
import lombok.Getter;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

@Getter
@Builder
public class StockPriceResponse {
    private String stockName;
    private String stockCode;
    private List<DailyPrice> prices;

    @Getter
    @Builder
    public static class DailyPrice {
        private LocalDate date;
        private BigDecimal closePrice;
    }
}
