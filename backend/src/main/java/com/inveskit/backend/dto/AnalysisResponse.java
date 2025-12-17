package com.inveskit.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.*;
import java.util.List;

@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AnalysisResponse {
    private List<TradeAnalysis> analysis;

    @JsonProperty("total_score")
    private Integer totalScore;

    @Getter
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TradeAnalysis {
        @JsonProperty("trade_id")
        private Integer tradeId;

        @JsonProperty("stock_name")
        private String stockName;
        private String type;
        private String advice;
    }
}