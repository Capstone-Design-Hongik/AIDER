package com.inveskit.backend.controller;

import com.inveskit.backend.dto.StockPriceResponse;
import com.inveskit.backend.service.StockPriceService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;

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
}
