package com.inveskit.backend.dto;

import lombok.*;

@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AnalysisResponse {
    private String strategy;
    private String summary;
    private String advice;
    private Metrics metrics;

    @Getter
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Metrics {
        private Integer totalTrades;
        private Double avgPrice;
        private Integer totalVolume;
    }
}