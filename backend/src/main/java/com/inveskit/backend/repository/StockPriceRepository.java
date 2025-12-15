package com.inveskit.backend.repository;

import com.inveskit.backend.domain.StockPrice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface StockPriceRepository extends JpaRepository<StockPrice, Long> {

    @Query("SELECT sp FROM StockPrice sp " +
            "WHERE sp.stockName = :stockName " +
            "AND sp.tradeDate BETWEEN :startDate AND :endDate " +
            "ORDER BY sp.tradeDate ASC")
    List<StockPrice> findByStockNameAndDateRange(
            @Param("stockName") String stockName,
            @Param("startDate") LocalDate startDate,
            @Param("endDate") LocalDate endDate
    );

    //특정 종목/날짜 데이터 존재 여부 확인
    boolean existsByStockCodeAndTradeDate(String stockCode, LocalDate tradeDate);

    //전체 데이터 개수 확인용
    long count();


    @Query("SELECT DISTINCT sp.stockName FROM StockPrice sp ORDER BY sp.stockName")
    List<String> findDistinctStockNames();
}
