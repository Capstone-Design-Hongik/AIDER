package com.inveskit.backend.controller;

import com.inveskit.backend.dto.StockDto;
import com.inveskit.backend.dto.StockPriceResponse;
import com.inveskit.backend.service.StockPriceService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/stocks")
@RequiredArgsConstructor
@Slf4j
public class StockController {
    private final StockPriceService stockPriceService;

    //특정 종목의 60일 주가 데이터 조회
    // GET /api/stocks/prices?stockName=삼성전자&endDate=2024-12-04
    @GetMapping("/prices")
    public ResponseEntity<StockPriceResponse> getStockPrices(
            @RequestParam String stockName,
            @RequestParam(required = false) LocalDate endDate
    ) {
        if (endDate == null) {
            endDate = LocalDate.now();
        }

        StockPriceResponse response = stockPriceService.getStockPrices(stockName, endDate);
        return ResponseEntity.ok(response);
    }

    //특정 종목 데이터 초기화 (2025.01.01 ~ 현재)
    // POST /api/stocks/initialize
    @PostMapping("/initialize")
    public ResponseEntity<String> initializeStockData(
            @RequestParam String stockName,
            @RequestParam String stockCode,
            @RequestParam(defaultValue = "KOSPI") String market
    ) {
        log.info("Initializing data for {} ({})", stockName, stockCode);
        stockPriceService.initializeStockData(stockName, stockCode, market);
        return ResponseEntity.ok("데이터 초기화 완료: " + stockName);
    }

    //DB에 저장된 전체 데이터 개수 확인
    // GET /api/stocks/count
    @GetMapping("/count")
    public ResponseEntity<Long> getDataCount() {
        long count = stockPriceService.getDataCount();
        return ResponseEntity.ok(count);
    }

    // 주요 종목 일괄 초기화
// POST /api/stocks/initialize-all
    @PostMapping("/initialize-all")
    public ResponseEntity<String> initializeAllStocks() {
        log.info("Starting bulk stock initialization");

        // KOSPI 주요 종목 리스트
        List<StockDto> majorStocks = List.of(
                new StockDto("삼성전자", "005930", "KOSPI"),
                new StockDto("SK하이닉스", "000660", "KOSPI"),
                new StockDto("LG에너지솔루션", "373220", "KOSPI"),
                new StockDto("삼성바이오로직스", "207940", "KOSPI"),
                new StockDto("현대차", "005380", "KOSPI"),
                new StockDto("기아", "000270", "KOSPI"),
                new StockDto("POSCO홀딩스", "005490", "KOSPI"),
                new StockDto("네이버", "035420", "KOSPI"),
                new StockDto("카카오", "035720", "KOSPI"),
                new StockDto("셀트리온", "068270", "KOSPI")
        );

        int successCount = 0;
        int failCount = 0;
        StringBuilder result = new StringBuilder();

        for (StockDto stock : majorStocks) {
            try {
                log.info("Initializing: {} ({})", stock.getName(), stock.getCode());
                stockPriceService.initializeStockData(
                        stock.getName(),
                        stock.getCode(),
                        stock.getMarket()
                );
                successCount++;
                result.append(String.format("✓ %s 완료\n", stock.getName()));
            } catch (Exception e) {
                failCount++;
                log.error("Failed to initialize {}: {}", stock.getName(), e.getMessage());
                result.append(String.format("✗ %s 실패: %s\n", stock.getName(), e.getMessage()));
            }
        }

        String summary = String.format(
                "=== 초기화 완료 ===\n성공: %d개\n실패: %d개\n\n%s",
                successCount, failCount, result.toString()
        );

        log.info("Bulk initialization completed. Success: {}, Failed: {}", successCount, failCount);
        return ResponseEntity.ok(summary);
    }
}
