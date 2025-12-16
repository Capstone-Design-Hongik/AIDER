package com.inveskit.backend.controller;

import com.inveskit.backend.dto.AnalysisRequest;
import com.inveskit.backend.dto.AnalysisResponse;
import com.inveskit.backend.dto.StockPriceResponse;
import com.inveskit.backend.dto.TradeResponse;
import com.inveskit.backend.service.AnalysisService;
import com.inveskit.backend.service.StockPriceService;
import com.inveskit.backend.service.TradeService;
import com.inveskit.backend.util.StockCodeMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@RestController
@RequestMapping("/api/analysis")
@RequiredArgsConstructor
public class AnalysisController {

    private final AnalysisService analysisService;
    private final TradeService tradeService;
    private final StockPriceService stockPriceService;

    @PostMapping
    public ResponseEntity<AnalysisResponse> analyzeTrading(
            @RequestBody AnalysisRequestDto requestDto
    ) {
        log.info("AI 분석 요청 수신 - strategy: {}, externalUrl: {}",
                requestDto.getStrategy(),
                requestDto.getExternalUrl());

        try {
            // 1. 모든 거래 내역 조회
            List<TradeResponse> trades = tradeService.getAllTrades();
            if (trades.isEmpty()) {
                throw new IllegalArgumentException("거래 내역이 없습니다.");
            }

            // 2. 첫 번째 종목명으로 주가 데이터 조회 (60일)
            String stockName = trades.get(0).getStockName();
            LocalDate latestTradeDate = trades.stream()
                    .map(TradeResponse::getDate)
                    .max(LocalDate::compareTo)
                    .orElse(LocalDate.now());

            StockPriceResponse stockPriceResponse = stockPriceService.getStockPrices(
                    stockName,
                    latestTradeDate
            );

            // 3. Flask API 요청 형식으로 변환
            List<AnalysisRequest.TradeInfo> tradeInfos = trades.stream()
                    .map(trade -> {
                        String stockCode = StockCodeMapper.getStockCode(trade.getStockName());
                        return AnalysisRequest.TradeInfo.builder()
                                .stockName(trade.getStockName())
                                .stockCode(stockCode)
                                .tradeType(trade.getTradeType())
                                .date(trade.getDate().toString())
                                .price(trade.getPrice())
                                .quantity(trade.getQuantity())
                                .build();
                    })
                    .collect(Collectors.toList());

            List<AnalysisRequest.StockPriceInfo> stockPriceInfos = stockPriceResponse.getPrices().stream()
                    .map(price -> AnalysisRequest.StockPriceInfo.builder()
                            .date(price.getDate().toString())
                            .closePrice(price.getClosePrice().doubleValue())
                            .build())
                    .collect(Collectors.toList());

            AnalysisRequest analysisRequest = AnalysisRequest.builder()
                    .trades(tradeInfos)
                    .stockPrices(stockPriceInfos)
                    .strategy(requestDto.getStrategy())
                    .externalUrl(requestDto.getExternalUrl())
                    .build();

            log.info("Flask API 호출 준비 완료 - trades: {}, prices: {}",
                    tradeInfos.size(),
                    stockPriceInfos.size());

            // 4. Flask API 호출
            AnalysisResponse response = analysisService.analyzeTrading(analysisRequest);

            log.info("AI 분석 완료");
            return ResponseEntity.ok(response);

        } catch (Exception e) {
            log.error("AI 분석 실패: {}", e.getMessage(), e);
            return ResponseEntity.badRequest().build();
        }
    }

    // 간단한 요청 DTO
    @lombok.Getter
    @lombok.Setter
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class AnalysisRequestDto {
        private String strategy;
        private String externalUrl;
    }
}