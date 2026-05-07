package com.inveskit.backend.repository;

import com.inveskit.backend.domain.SavedStrategy;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface SavedStrategyRepository extends JpaRepository<SavedStrategy, Long> {
    List<SavedStrategy> findAllByOrderBySavedAtDesc();
    boolean existsByUrl(String url);
}
