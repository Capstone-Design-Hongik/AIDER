package com.inveskit.backend.domain;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "stock_prices",
        uniqueConstraints = {
                @UniqueConstraint(columnNames = {"stock_code", "trade_date"})
        },
        indexes = {
                @Index(name = "idx_stock_name", columnList = "stock_name"),
                @Index(name = "idx_trade_date", columnList = "trade_date")
        })
@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class StockPrice {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 10)
    private String stockCode;  // 005930

    @Column(nullable = false, length = 50)
    private String stockName;  // 삼성전자

    @Column(nullable = false, length = 10)
    private String market;  // KOSPI, KOSDAQ

    @Column(nullable = false)
    private LocalDate tradeDate;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal closePrice;  // 종가

    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
