package com.inveskit.backend.scheduler;

import com.inveskit.backend.domain.StockInfo;
import com.inveskit.backend.service.StockInfoService;
import com.inveskit.backend.service.StockPriceService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.List;

@Component
@RequiredArgsConstructor
@Slf4j
public class StockPriceScheduler {

    private static final long DELAY_BETWEEN_STOCKS_MS = 100L;
    private static final LocalDate INITIAL_START_DATE = LocalDate.of(2025, 1, 1);

    private final StockInfoService stockInfoService;
    private final StockPriceService stockPriceService;

    // 앱 시작 완료 후 백그라운드에서 전종목 수집
    // DB가 비어있으면 2025-01-01부터, 이미 데이터가 있으면 당일치만 수집
    @Async("stockPriceExecutor")
    @EventListener(ApplicationReadyEvent.class)
    public void collectOnStartup() {
        long existingCount = stockPriceService.getDataCount();
        if (existingCount == 0) {
            log.info("[스케줄러] 초기 기동 - 2025-01-01부터 전종목 주가 수집 시작");
            collectAllStockPrices(INITIAL_START_DATE, LocalDate.now());
            log.info("[스케줄러] 초기 기동 - 전종목 주가 수집 완료");
        } else {
            log.info("[스케줄러] 기존 데이터 {}건 존재 - 당일치만 수집", existingCount);
            collectAllStockPrices(LocalDate.now(), LocalDate.now());
            log.info("[스케줄러] 당일치 수집 완료");
        }
    }

    // 매일 평일 오후 4시 당일 종가 업데이트
    @Scheduled(cron = "0 0 16 * * MON-FRI", zone = "Asia/Seoul")
    public void collectDaily() {
        log.info("[스케줄러] 일일 스케줄 - 전종목 당일 종가 수집 시작");
        collectAllStockPrices(LocalDate.now(), LocalDate.now());
        log.info("[스케줄러] 일일 스케줄 - 전종목 당일 종가 수집 완료");
    }

    private void collectAllStockPrices(LocalDate startDate, LocalDate endDate) {
        LocalDate today = LocalDate.now();
        DayOfWeek dayOfWeek = today.getDayOfWeek();
        if (dayOfWeek == DayOfWeek.SATURDAY || dayOfWeek == DayOfWeek.SUNDAY) {
            log.info("[스케줄러] 주말이므로 수집을 스킵합니다. ({})", dayOfWeek);
            return;
        }

        List<StockInfo> allStocks = stockInfoService.findAll();
        if (allStocks.isEmpty()) {
            log.warn("[스케줄러] stock_info 테이블이 비어있습니다. 수집 중단.");
            return;
        }

        log.info("[스케줄러] 수집 대상: {}개 종목 ({} ~ {})", allStocks.size(), startDate, endDate);

        int totalSaved = 0;
        int successCount = 0;
        int failCount = 0;

        for (int i = 0; i < allStocks.size(); i++) {
            StockInfo stock = allStocks.get(i);
            try {
                int saved = stockPriceService.fetchAndSavePrices(stock, startDate, endDate);
                totalSaved += saved;
                successCount++;

                if ((i + 1) % 100 == 0) {
                    log.info("[스케줄러] 진행: {}/{} 종목 처리 완료 (신규 저장: {}건)",
                            i + 1, allStocks.size(), totalSaved);
                }
            } catch (Exception e) {
                failCount++;
                log.error("[스케줄러] {} ({}) 수집 실패: {}",
                        stock.getStockName(), stock.getStockCode(), e.getMessage());
            }

            sleep(DELAY_BETWEEN_STOCKS_MS);
        }

        log.info("[스케줄러] 수집 완료 - 성공: {}, 실패: {}, 신규 저장: {}건",
                successCount, failCount, totalSaved);
    }

    private void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("[스케줄러] 수집 중 인터럽트 발생");
        }
    }
}
