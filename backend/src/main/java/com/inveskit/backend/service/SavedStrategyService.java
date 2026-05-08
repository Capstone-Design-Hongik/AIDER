package com.inveskit.backend.service;

import com.inveskit.backend.domain.SavedStrategy;
import com.inveskit.backend.repository.SavedStrategyRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;

@Service
@RequiredArgsConstructor
public class SavedStrategyService {

    private final SavedStrategyRepository savedStrategyRepository;

    public List<SavedStrategy> findAll() {
        return savedStrategyRepository.findAllByOrderBySavedAtDesc();
    }

    @Transactional
    public SavedStrategy save(String url, String name) {
        if (savedStrategyRepository.existsByUrl(url)) {
            throw new IllegalArgumentException("이미 저장된 URL입니다.");
        }
        return savedStrategyRepository.save(
            SavedStrategy.builder()
                .url(url)
                .name(name)
                .savedAt(LocalDate.now())
                .build()
        );
    }

    @Transactional
    public void delete(Long id) {
        savedStrategyRepository.deleteById(id);
    }
}
