package com.inveskit.backend.dto;

import com.inveskit.backend.domain.Trade;
import com.inveskit.backend.util.StockCodeMapper;
import lombok.*;

import java.time.LocalDate;


@Getter
@NoArgsConstructor
@AllArgsConstructor
public class TradeCreateRequest {
    private String stockName;
    private String tradeType;  // buy , sell
    private LocalDate date;
    private Double price;
    private Integer quantity;

    public Trade toEntity() {

        String stockCode = StockCodeMapper.getStockCode(stockName);

        return Trade.builder()
                .stockName(stockName)
                .stockCode(stockCode)
                .tradeType(tradeType.equalsIgnoreCase("buy") ? Trade.TradeType.BUY : Trade.TradeType.SELL)
                .tradeDate(date)
                .price(price)
                .quantity(quantity)
                .build();
    }
}