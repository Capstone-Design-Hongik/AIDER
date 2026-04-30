package com.inveskit.backend.service;

import com.inveskit.backend.domain.AnalysisResult;
import com.inveskit.backend.domain.StockPrice;
import com.inveskit.backend.repository.AnalysisResultRepository;
import com.inveskit.backend.repository.StockPriceRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class AnalysisResultService {

    private final AnalysisResultRepository analysisResultRepository;
    private final StockPriceRepository stockPriceRepository;

    @Transactional
    public AnalysisResult save(String stockName, String stockCode, String signal, Double priceAtAnalysis) {
        AnalysisResult result = AnalysisResult.builder()
                .stockName(stockName)
                .stockCode(stockCode)
                .signal(signal)
                .priceAtAnalysis(priceAtAnalysis)
                .analysisDate(LocalDate.now())
                .evaluationDate(LocalDate.now().plusDays(30))
                .build();
        return analysisResultRepository.save(result);
    }

    @Transactional
    public List<Map<String, Object>> getPerformance() {
        // 평가일이 지났는데 아직 평가 안 된 것들 먼저 업데이트
        evaluatePending();

        return analysisResultRepository.findAllByOrderByAnalysisDateDesc()
                .stream()
                .map(this::toResponseMap)
                .collect(Collectors.toList());
    }

    private void evaluatePending() {
        List<AnalysisResult> pending = analysisResultRepository
                .findByEvaluationDateLessThanEqualAndPriceAtEvaluationIsNull(LocalDate.now());

        for (AnalysisResult r : pending) {
            // 평가일 기준 가장 가까운 주가 조회 (±7일 범위)
            List<StockPrice> prices = stockPriceRepository.findByStockNameAndDateRange(
                    r.getStockName(),
                    r.getEvaluationDate().minusDays(7),
                    r.getEvaluationDate().plusDays(7)
            );

            if (!prices.isEmpty()) {
                // 평가일에 가장 가까운 날짜의 주가 선택
                StockPrice closest = prices.stream()
                        .min((a, b) -> {
                            long diffA = Math.abs(a.getTradeDate().toEpochDay() - r.getEvaluationDate().toEpochDay());
                            long diffB = Math.abs(b.getTradeDate().toEpochDay() - r.getEvaluationDate().toEpochDay());
                            return Long.compare(diffA, diffB);
                        })
                        .get();

                r.evaluate(closest.getClosePrice().doubleValue());
                analysisResultRepository.save(r);
                log.info("성과 평가 완료 - {}: {} → {} ({})",
                        r.getStockName(), r.getPriceAtAnalysis(), closest.getClosePrice(), r.getIsCorrect());
            }
        }
    }

    private Map<String, Object> toResponseMap(AnalysisResult r) {
        Map<String, Object> map = new java.util.LinkedHashMap<>();
        map.put("id", r.getId());
        map.put("stockName", r.getStockName());
        map.put("stockCode", r.getStockCode());
        map.put("signal", r.getSignal());
        map.put("priceAtAnalysis", r.getPriceAtAnalysis());
        map.put("analysisDate", r.getAnalysisDate().toString());
        map.put("evaluationDate", r.getEvaluationDate().toString());
        map.put("priceAtEvaluation", r.getPriceAtEvaluation());
        map.put("isCorrect", r.getIsCorrect());
        return map;
    }
}
