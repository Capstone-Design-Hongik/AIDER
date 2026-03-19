package com.inveskit.backend.config;

import com.inveskit.backend.service.StockInfoService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class StockInfoInitializer implements ApplicationRunner {

    private final StockInfoService stockInfoService;

    @Override
    public void run(ApplicationArguments args) {
        log.info("종목 정보 초기화 확인 중...");
        stockInfoService.syncIfEmpty();
    }
}
