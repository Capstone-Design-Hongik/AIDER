package com.inveskit.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.*;

@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AnalysisResponse {
    private String type;
    private String signal;
    private String evaluation;
    private String advice;

    @JsonProperty("total_score")
    private Double totalScore;
}
