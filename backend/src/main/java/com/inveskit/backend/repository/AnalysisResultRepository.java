package com.inveskit.backend.repository;

import com.inveskit.backend.domain.AnalysisResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface AnalysisResultRepository extends JpaRepository<AnalysisResult, Long> {

    List<AnalysisResult> findAllByOrderByAnalysisDateDesc();

    // 평가일이 지났는데 아직 평가 안 된 것들
    List<AnalysisResult> findByEvaluationDateLessThanEqualAndPriceAtEvaluationIsNull(LocalDate date);
}
