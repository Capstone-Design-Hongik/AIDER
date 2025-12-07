package com.inveskit.backend.repository;

import com.inveskit.backend.domain.Trade;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface TradeRepository extends JpaRepository<Trade, Long> {

    // 특정 종목의 거래 내역 조회
    List<Trade> findByStockName(String stockName);

    // 특정 기간 거래 내역 조회
    List<Trade> findByTradeDateBetween(LocalDate startDate, LocalDate endDate);

    // 전체 거래 내역 최신순 조회
    List<Trade> findAllByOrderByTradeDateDesc();
}