package io.copybarca.transapi.service;

import org.springframework.web.multipart.MultipartFile;

public interface BookFileStorage {

    String storeOriginal(Long bookId, MultipartFile file);
    String storeAsset(Long bookId, MultipartFile file);

    String storeTranslated(Long bookId, MultipartFile file);
    String storeTranslated(Long bookId, byte[] pdf);


    byte[] read(String location);
}
