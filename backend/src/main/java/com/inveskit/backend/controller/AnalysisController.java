package com.inveskit.backend.controller;

import com.inveskit.backend.dto.AnalysisRequest;
import com.inveskit.backend.dto.AnalysisResponse;
import com.inveskit.backend.dto.StockPriceResponse;
import com.inveskit.backend.dto.TradeResponse;
import com.inveskit.backend.service.AnalysisResultService;
import com.inveskit.backend.service.AnalysisService;
import com.inveskit.backend.service.StockInfoService;
import com.inveskit.backend.service.StockPriceService;
import com.inveskit.backend.service.TradeService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@RestController
@RequestMapping("/api/analysis")
@RequiredArgsConstructor
public class AnalysisController {

    private final AnalysisService analysisService;
    private final AnalysisResultService analysisResultService;
    private final TradeService tradeService;
    private final StockPriceService stockPriceService;
    private final StockInfoService stockInfoService;

    @PostMapping
    public ResponseEntity<Map<String, Object>> analyzeTrading(
            @RequestBody AnalysisRequestDto requestDto
    ) {
        log.info("AI 분석 요청 수신 - strategy: {}, externalUrl: {}",
                requestDto.getStrategy(),
                requestDto.getExternalUrl());

        try {
            // 1. 거래 내역 조회 (선택 종목으로 필터링)
            List<TradeResponse> allTrades = tradeService.getAllTrades();
            if (allTrades.isEmpty()) {
                throw new IllegalArgumentException("거래 내역이 없습니다.");
            }

            String stockName = (requestDto.getStockName() != null && !requestDto.getStockName().isBlank())
                    ? requestDto.getStockName()
                    : allTrades.get(0).getStockName();

            List<TradeResponse> trades = allTrades.stream()
                    .filter(t -> t.getStockName().equals(stockName))
                    .collect(Collectors.toList());

            if (trades.isEmpty()) {
                throw new IllegalArgumentException("선택한 종목의 거래 내역이 없습니다: " + stockName);
            }

            // 2. 선택 종목 주가 데이터 조회 (60일)
            LocalDate latestTradeDate = trades.stream()
                    .map(TradeResponse::getDate)
                    .max(LocalDate::compareTo)
                    .orElse(LocalDate.now());

            StockPriceResponse stockPriceResponse = stockPriceService.getStockPrices(
                    stockName,
                    null,
                    latestTradeDate
            );

            // 3. Flask API 요청 형식으로 변환
            List<AnalysisRequest.TradeInfo> tradeInfos = trades.stream()
                    .map(trade -> {
                        String stockCode = stockInfoService.findByName(trade.getStockName()).getStockCode();
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

            // 4-1. scores 평균으로 totalScore 계산
            Map<String, Double> scores = response.getScores();
            double totalScore = (scores != null && !scores.isEmpty())
                    ? scores.values().stream().mapToDouble(Double::doubleValue).average().orElse(0)
                    : 0.0;
            long roundedScore = Math.round(totalScore);
            // 프론트 표시용으로 각 점수도 정수 반올림
            Map<String, Long> roundedScores = scores != null
                    ? scores.entrySet().stream().collect(
                          java.util.stream.Collectors.toMap(
                              Map.Entry::getKey,
                              e -> Math.round(e.getValue())
                          ))
                    : Map.of();

            // 5. 분석 결과 DB 저장 (AI 성과 추적용)
            Double latestPrice = stockPriceInfos.isEmpty() ? null
                    : stockPriceInfos.get(stockPriceInfos.size() - 1).getClosePrice();
            String stockCode = tradeInfos.get(0).getStockCode();

            if (latestPrice != null && response.getSignal() != null) {
                analysisResultService.save(
                        stockName, stockCode, response.getSignal(), latestPrice, latestTradeDate,
                        requestDto.getStrategy(), response.getAdvice(), response.getEvaluation(), totalScore
                );
                log.info("분석 결과 저장 완료 - {}, signal: {}, price: {}, lastTradeDate: {}",
                        stockName, response.getSignal(), latestPrice, latestTradeDate);
            }

            // 6. 프론트엔드 응답 구성
            Map<String, Object> analysisItem = new HashMap<>();
            analysisItem.put("stockName", stockName);
            analysisItem.put("type", response.getType());
            analysisItem.put("advice", response.getAdvice());
            analysisItem.put("signal", response.getSignal());
            analysisItem.put("evaluation", response.getEvaluation());

            Map<String, Object> result = new HashMap<>();
            result.put("total_score", roundedScore);
            result.put("scores", roundedScores);
            result.put("signal", response.getSignal());
            result.put("analysis", List.of(analysisItem));

            log.info("AI 분석 완료 - signal: {}, total_score: {}", response.getSignal(), roundedScore);
            return ResponseEntity.ok(result);

        } catch (Exception e) {
            log.error("AI 분석 실패: {}", e.getMessage(), e);
            return ResponseEntity.badRequest().build();
        }
    }

    @GetMapping("/performance")
    public ResponseEntity<List<Map<String, Object>>> getPerformance() {
        return ResponseEntity.ok(analysisResultService.getPerformance());
    }

    @DeleteMapping("/performance/{id}")
    public ResponseEntity<String> deleteAnalysisResult(@PathVariable Long id) {
        analysisResultService.delete(id);
        return ResponseEntity.ok("분석 결과가 삭제되었습니다.");
    }

    // 간단한 요청 DTO
    @lombok.Getter
    @lombok.Setter
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class AnalysisRequestDto {
        private String strategy;
        private String externalUrl;
        private String stockName;
    }
}