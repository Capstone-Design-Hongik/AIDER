package com.inveskit.backend.controller;

import com.inveskit.backend.dto.StockPriceResponse;
import com.inveskit.backend.service.StockInfoService;
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
    private final StockInfoService stockInfoService;

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

    // 특정 종목 주가 초기화 (stock_info에서 코드 자동 조회)
    // POST /api/stocks/initialize?stockName=카카오뱅크
    @PostMapping("/initialize")
    public ResponseEntity<String> initializeStockData(@RequestParam String stockName) {
        log.info("Initializing data for {}", stockName);
        stockPriceService.initializeStockData(stockName);
        return ResponseEntity.ok("데이터 초기화 완료: " + stockName);
    }

    // 주요 종목 일괄 주가 초기화 (stock_info에서 코드 조회)
    // POST /api/stocks/initialize-all
    @PostMapping("/initialize-all")
    public ResponseEntity<String> initializeAllStocks() {
        List<String> majorStocks = List.of(
                "삼성전자", "SK하이닉스", "LG에너지솔루션", "삼성바이오로직스",
                "현대차", "기아", "POSCO홀딩스", "NAVER", "카카오", "셀트리온"
        );

        int successCount = 0;
        int failCount = 0;
        StringBuilder result = new StringBuilder();

        for (String stockName : majorStocks) {
            try {
                stockPriceService.initializeStockData(stockName);
                successCount++;
                result.append(String.format("✓ %s 완료\n", stockName));
            } catch (Exception e) {
                failCount++;
                log.error("Failed to initialize {}: {}", stockName, e.getMessage());
                result.append(String.format("✗ %s 실패: %s\n", stockName, e.getMessage()));
            }
        }

        String summary = String.format(
                "=== 초기화 완료 ===\n성공: %d개\n실패: %d개\n\n%s",
                successCount, failCount, result.toString()
        );
        return ResponseEntity.ok(summary);
    }

    // DB에 저장된 주가 데이터 개수
    // GET /api/stocks/count
    @GetMapping("/count")
    public ResponseEntity<Long> getDataCount() {
        return ResponseEntity.ok(stockPriceService.getDataCount());
    }

    // 종목 검색 자동완성 (stock_info 전체에서 검색)
    // GET /api/stocks/search?keyword=삼성
    @GetMapping("/search")
    public ResponseEntity<List<String>> searchStocks(@RequestParam String keyword) {
        List<String> results = stockPriceService.searchStockNames(keyword);
        return ResponseEntity.ok(results);
    }

    // KRX 종목 목록 동기화 (수동 트리거)
    // POST /api/stocks/sync-krx
    @PostMapping("/sync-krx")
    public ResponseEntity<String> syncFromKrx() {
        log.info("KRX 종목 동기화 수동 트리거");
        int count = stockInfoService.syncFromKrx();
        return ResponseEntity.ok(String.format("KRX 종목 동기화 완료: %d개", count));
    }

    // stock_info 테이블 종목 수 확인
    // GET /api/stocks/info/count
    @GetMapping("/info/count")
    public ResponseEntity<Long> getStockInfoCount() {
        return ResponseEntity.ok(stockInfoService.count());
    }
}
