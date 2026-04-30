package com.inveskit.backend.domain;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "analysis_results")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class AnalysisResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String stockName;

    @Column(nullable = false)
    private String stockCode;

    @Column(nullable = false)
    private String signal; // buy / sell / hold

    @Column(nullable = false)
    private Double priceAtAnalysis;

    @Column(nullable = false)
    private LocalDate analysisDate;

    @Column(nullable = false)
    private LocalDate evaluationDate; // analysisDate + 30일

    private Double priceAtEvaluation; // 평가일 주가 (30일 후 조회)

    private Boolean isCorrect; // 적중 여부

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }

    public void evaluate(Double priceAtEvaluation) {
        this.priceAtEvaluation = priceAtEvaluation;
        this.isCorrect = switch (this.signal) {
            case "buy"  -> priceAtEvaluation > this.priceAtAnalysis;
            case "sell" -> priceAtEvaluation < this.priceAtAnalysis;
            case "hold" -> priceAtEvaluation >= this.priceAtAnalysis;
            default     -> false;
        };
    }
}
