package com.inveskit.backend.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.*;

import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AnalysisResponse {
    private String type;
    private String signal;
    private String evaluation;
    private String advice;
    private Map<String, Integer> scores;
}
