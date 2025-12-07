package com.inveskit.backend.service;

import com.inveskit.backend.domain.Trade;
import com.inveskit.backend.dto.TradeCreateRequest;
import com.inveskit.backend.dto.TradeResponse;
import com.inveskit.backend.repository.TradeRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class TradeService {

    private final TradeRepository tradeRepository;

    // 거래 생성
    @Transactional
    public TradeResponse createTrade(TradeCreateRequest request) {
        log.info("Creating trade: {} {} on {}",
                request.getStockName(), request.getTradeType(), request.getDate());

        Trade trade = request.toEntity();
        Trade saved = tradeRepository.save(trade);

        return TradeResponse.from(saved);
    }

    // 전체 거래 조회 (최신순)
    @Transactional(readOnly = true)
    public List<TradeResponse> getAllTrades() {
        return tradeRepository.findAllByOrderByTradeDateDesc()
                .stream()
                .map(TradeResponse::from)
                .collect(Collectors.toList());
    }

    // 특정 거래 조회
    @Transactional(readOnly = true)
    public TradeResponse getTrade(Long id) {
        Trade trade = tradeRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("거래 내역을 찾을 수 없습니다: " + id));

        return TradeResponse.from(trade);
    }

    // 특정 종목의 거래 조회
    @Transactional(readOnly = true)
    public List<TradeResponse> getTradesByStock(String stockName) {
        return tradeRepository.findByStockName(stockName)
                .stream()
                .map(TradeResponse::from)
                .collect(Collectors.toList());
    }

    // 거래 삭제
    @Transactional
    public void deleteTrade(Long id) {
        log.info("Deleting trade: {}", id);

        if (!tradeRepository.existsById(id)) {
            throw new RuntimeException("거래 내역을 찾을 수 없습니다: " + id);
        }

        tradeRepository.deleteById(id);
    }

    // 전체 거래 개수
    @Transactional(readOnly = true)
    public long getTradeCount() {
        return tradeRepository.count();
    }
}