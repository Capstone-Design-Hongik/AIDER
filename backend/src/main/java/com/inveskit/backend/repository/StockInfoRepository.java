package com.inveskit.backend.repository;

import com.inveskit.backend.domain.StockInfo;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface StockInfoRepository extends JpaRepository<StockInfo, String> {

    Optional<StockInfo> findByStockName(String stockName);

    List<StockInfo> findByStockNameContainingOrderByStockName(String keyword);
}
