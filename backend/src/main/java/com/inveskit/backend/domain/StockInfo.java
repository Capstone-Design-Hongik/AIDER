package com.inveskit.backend.domain;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(name = "stock_info")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class StockInfo {

    @Id
    @Column(length = 10)
    private String stockCode;   // 005930

    @Column(nullable = false, length = 100)
    private String stockName;   // 삼성전자

    @Column(nullable = false, length = 10)
    private String market;      // KOSPI / KOSDAQ

    private LocalDateTime updatedAt;

    @PrePersist
    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
