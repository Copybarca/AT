package io.copybarca.transapi.service;

import io.copybarca.transapi.model.ProcessStatus;
import io.copybarca.transapi.repo.PdfBuildProcessRepository;
import io.copybarca.transapi.repo.PdfExtractionProcessRepository;
import io.copybarca.transapi.repo.TranslationProcessRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
public class PipelineFailureService {

    private final PdfExtractionProcessRepository extractions;
    private final TranslationProcessRepository translations;
    private final PdfBuildProcessRepository builds;

    public PipelineFailureService(
            PdfExtractionProcessRepository extractions,
            TranslationProcessRepository translations,
            PdfBuildProcessRepository builds
    ) {
        this.extractions = extractions;
        this.translations = translations;
        this.builds = builds;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void failExtraction(Long processId) {
        extractions.findById(processId).ifPresent(process -> {
            if (process.getStatus() == ProcessStatus.IN_PROGRESS) {
                process.fail();
            }
        });
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void failTranslation(Long processId) {
        translations.findById(processId).ifPresent(process -> {
            if (process.getStatus() == ProcessStatus.IN_PROGRESS) {
                process.fail();
            }
        });
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void failBuild(Long processId) {
        builds.findById(processId).ifPresent(process -> {
            if (process.getStatus() == ProcessStatus.IN_PROGRESS) {
                process.fail();
            }
        });
    }
}
