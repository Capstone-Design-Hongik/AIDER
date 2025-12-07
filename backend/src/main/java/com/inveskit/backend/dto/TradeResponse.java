package com.inveskit.backend.dto;

import com.inveskit.backend.domain.Trade;
import lombok.*;

import java.time.LocalDate;

// 거래 응답
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TradeResponse {
    private Long id;
    private String stockName;
    private String tradeType;  // buy or sell
    private LocalDate date;
    private Double price;
    private Integer quantity;

    public static TradeResponse from(Trade trade) {
        return TradeResponse.builder()
                .id(trade.getId())
                .stockName(trade.getStockName())
                .tradeType(trade.getTradeType().name().toLowerCase())
                .date(trade.getTradeDate())
                .price(trade.getPrice())
                .quantity(trade.getQuantity())
                .build();
    }
}