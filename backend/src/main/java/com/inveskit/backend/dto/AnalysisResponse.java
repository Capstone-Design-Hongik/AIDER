package com.inveskit.backend.dto;

import lombok.*;
import java.util.List;

@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AnalysisResponse {
    private List<TradeAnalysis> analysis;
    private Integer totalScore;

    @Getter
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TradeAnalysis {
        private Integer tradeId;
        private String stockName;
        private String type;
        private String advice;
    }
}