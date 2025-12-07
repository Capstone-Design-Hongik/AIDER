package com.inveskit.backend.controller;

import com.inveskit.backend.dto.TradeCreateRequest;
import com.inveskit.backend.dto.TradeResponse;
import com.inveskit.backend.service.TradeService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/trades")
@RequiredArgsConstructor
@Slf4j
public class TradeController {

    private final TradeService tradeService;

    // 거래 생성
    // POST /api/trades
    @PostMapping
    public ResponseEntity<TradeResponse> createTrade(@RequestBody TradeCreateRequest request) {
        log.info("Creating new trade: {}", request.getStockName());
        TradeResponse response = tradeService.createTrade(request);
        return ResponseEntity.ok(response);
    }

    // 전체 거래 조회
    // GET /api/trades
    @GetMapping
    public ResponseEntity<List<TradeResponse>> getAllTrades() {
        List<TradeResponse> trades = tradeService.getAllTrades();
        return ResponseEntity.ok(trades);
    }

    // 특정 거래 조회
    // GET /api/trades/{id}
    @GetMapping("/{id}")
    public ResponseEntity<TradeResponse> getTrade(@PathVariable Long id) {
        TradeResponse trade = tradeService.getTrade(id);
        return ResponseEntity.ok(trade);
    }

    // 특정 종목의 거래 조회
    // GET /api/trades/stock/{stockName}
    @GetMapping("/stock/{stockName}")
    public ResponseEntity<List<TradeResponse>> getTradesByStock(@PathVariable String stockName) {
        List<TradeResponse> trades = tradeService.getTradesByStock(stockName);
        return ResponseEntity.ok(trades);
    }

    // 거래 삭제
    // DELETE /api/trades/{id}
    @DeleteMapping("/{id}")
    public ResponseEntity<String> deleteTrade(@PathVariable Long id) {
        log.info("Deleting trade: {}", id);
        tradeService.deleteTrade(id);
        return ResponseEntity.ok("거래 내역이 삭제되었습니다.");
    }

    // 전체 거래 개수
    // GET /api/trades/count
    @GetMapping("/count")
    public ResponseEntity<Long> getTradeCount() {
        long count = tradeService.getTradeCount();
        return ResponseEntity.ok(count);
    }
}