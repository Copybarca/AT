package io.copybarca.transapi.service;

import org.springframework.web.multipart.MultipartFile;

public interface BookFileStorage {

    String storeOriginal(Long bookId, MultipartFile file);

    String storeTranslated(Long bookId, MultipartFile file);
}
