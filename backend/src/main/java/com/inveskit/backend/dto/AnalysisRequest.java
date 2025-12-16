package com.inveskit.backend.dto;

import lombok.*;
import java.util.List;

@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AnalysisRequest {
    private List<TradeInfo> trades;
    private List<StockPriceInfo> stockPrices;
    private String strategy;
    private String externalUrl;

    @Getter
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TradeInfo {
        private String stockName;
        private String stockCode;
        private String tradeType;
        private String date;
        private Double price;
        private Integer quantity;
    }

    @Getter
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class StockPriceInfo {
        private String date;
        private Double closePrice;
    }
}