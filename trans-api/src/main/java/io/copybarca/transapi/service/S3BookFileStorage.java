package io.copybarca.transapi.service;

import io.copybarca.transapi.service.exception.BookStorageException;
import jakarta.annotation.PreDestroy;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.core.exception.SdkException;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.http.urlconnection.UrlConnectionHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.S3Configuration;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;

@Service
public class S3BookFileStorage implements BookFileStorage {

    private final S3Client s3Client;
    private final String bucket;
    private final String prefix;

    public S3BookFileStorage(
            @Value("${storage.s3.bucket}") String bucket,
            @Value("${storage.s3.prefix}") String prefix,
            @Value("${storage.s3.region}") String region,
            @Value("${storage.s3.endpoint:}") String endpoint,
            @Value("${storage.s3.path-style-access:false}") boolean pathStyleAccess,
            @Value("${storage.s3.access-key:}") String accessKey,
            @Value("${storage.s3.secret-key:}") String secretKey
    ) {
        this.bucket = bucket;
        this.prefix = normalizePrefix(prefix);

        var builder = S3Client.builder()
                .region(Region.of(region))
                .httpClientBuilder(UrlConnectionHttpClient.builder())
                .serviceConfiguration(S3Configuration.builder()
                        .pathStyleAccessEnabled(pathStyleAccess)
                        .build());

        if (StringUtils.hasText(endpoint)) {
            builder.endpointOverride(URI.create(endpoint));
        }
        if (StringUtils.hasText(accessKey) != StringUtils.hasText(secretKey)) {
            throw new IllegalStateException("S3 access key and secret key must be configured together");
        }
        if (StringUtils.hasText(accessKey)) {
            builder.credentialsProvider(StaticCredentialsProvider.create(
                    AwsBasicCredentials.create(accessKey, secretKey)
            ));
        }

        this.s3Client = builder.build();
    }

    @Override
    public String storeOriginal(Long bookId, MultipartFile file) {
        return store(bookId, "original", file);
    }

    @Override
    public String storeAsset(Long bookId, MultipartFile file) {
        return store(bookId, "assets", file);
    }

    @Override
    public String storeTranslated(Long bookId, MultipartFile file) {
        return store(bookId, "translated", file);
    }

    @Override
    public String storeTranslated(Long bookId, byte[] pdf) {
        String key = "%s/%d/translated/%s-result.pdf".formatted(
                prefix,
                bookId,
                UUID.randomUUID()
        );
        try {
            s3Client.putObject(
                    PutObjectRequest.builder()
                            .bucket(bucket)
                            .key(key)
                            .contentType("application/pdf")
                            .build(),
                    RequestBody.fromBytes(pdf)
            );
            return "s3://%s/%s".formatted(bucket, key);
        } catch (SdkException exception) {
            throw new BookStorageException(
                    "Could not upload translated PDF to S3",
                    exception
            );
        }
    }


    @Override
    public byte[] read(String location) {
        URI uri = URI.create(location);
        if (!"s3".equalsIgnoreCase(uri.getScheme())
                || !StringUtils.hasText(uri.getHost())
                || !StringUtils.hasText(uri.getPath())) {
            throw new BookStorageException(
                    "Stored book path is not a valid S3 URI",
                    new IllegalArgumentException(location)
            );
        }
        try {
            return s3Client.getObjectAsBytes(
                    GetObjectRequest.builder()
                            .bucket(uri.getHost())
                            .key(uri.getPath().substring(1))
                            .build()
            ).asByteArray();
        } catch (SdkException exception) {
            throw new BookStorageException("Could not read book file from S3", exception);
        }
    }

    private String store(Long bookId, String kind, MultipartFile file) {

        String filename = sanitizeFilename(file.getOriginalFilename());
        String key = "%s/%d/%s/%s-%s".formatted(
                prefix,
                bookId,
                kind,
                UUID.randomUUID(),
                filename
        );

        var request = PutObjectRequest.builder()
                .bucket(bucket)
                .key(key);
        if (StringUtils.hasText(file.getContentType())) {
            request.contentType(file.getContentType());
        }

        try (InputStream input = file.getInputStream()) {
            s3Client.putObject(request.build(), RequestBody.fromInputStream(input, file.getSize()));
            return "s3://%s/%s".formatted(bucket, key);
        } catch (IOException | SdkException exception) {
            throw new BookStorageException("Could not upload book file to S3", exception);
        }
    }

    private static String normalizePrefix(String value) {
        String normalized = value == null ? "books" : value.replaceAll("^/+|/+$", "");
        return normalized.isBlank() ? "books" : normalized;
    }

    private static String sanitizeFilename(String originalFilename) {
        String filename = StringUtils.hasText(originalFilename) ? originalFilename : "file";
        filename = filename.replace('\\', '/');
        filename = filename.substring(filename.lastIndexOf('/') + 1);
        filename = filename.replaceAll("[\\p{Cntrl}]", "_").trim();
        return filename.isBlank() ? "file" : filename;
    }

    @PreDestroy
    void close() {
        s3Client.close();
    }
}
