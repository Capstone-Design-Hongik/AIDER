package com.inveskit.backend.service;

import com.inveskit.backend.client.CsvStockLoader;
import com.inveskit.backend.client.KrxStockListClient;
import com.inveskit.backend.domain.StockInfo;
import com.inveskit.backend.repository.StockInfoRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class StockInfoService {

    private final StockInfoRepository stockInfoRepository;
    private final KrxStockListClient krxStockListClient;
    private final CsvStockLoader csvStockLoader;

    // KRX에서 전체 종목 받아서 DB 저장, 실패 시 CSV 폴백
    @Transactional
    public int syncFromKrx() {
        log.info("KRX 종목 동기화 시작");
        List<StockInfo> stocks = krxStockListClient.fetchAllStocks();

        if (stocks.isEmpty()) {
            log.warn("KRX API 실패 - 번들 CSV에서 로드합니다");
            stocks = csvStockLoader.loadFromCsv();
        }

        if (stocks.isEmpty()) {
            log.error("KRX와 CSV 모두 종목을 가져오지 못했습니다");
            return 0;
        }

        stockInfoRepository.saveAll(stocks);
        log.info("종목 동기화 완료: {}개", stocks.size());
        return stocks.size();
    }

    // DB가 비어있을 때만 자동 동기화 (앱 시작 시 호출)
    @Transactional
    public void syncIfEmpty() {
        long count = stockInfoRepository.count();
        if (count == 0) {
            log.info("stock_info 테이블이 비어있어 종목 동기화를 자동 실행합니다");
            syncFromKrx();
        } else {
            log.info("stock_info 테이블에 {}개 종목 존재, 동기화 스킵", count);
        }
    }

    // 종목명으로 코드 조회
    public StockInfo findByName(String stockName) {
        return stockInfoRepository.findByStockName(stockName)
                .orElseThrow(() -> new RuntimeException("등록되지 않은 종목입니다: " + stockName));
    }

    // 키워드로 종목 검색 (자동완성)
    @Transactional(readOnly = true)
    public List<String> searchByKeyword(String keyword) {
        return stockInfoRepository.findByStockNameContainingOrderByStockName(keyword)
                .stream()
                .map(StockInfo::getStockName)
                .limit(10)
                .toList();
    }

    public long count() {
        return stockInfoRepository.count();
    }
}
