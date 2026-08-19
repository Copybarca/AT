package io.copybarca.transapi.service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class InternalServiceAuthorizer {

    private final byte[] expected;

    public InternalServiceAuthorizer(
            @Value("${internal.service-token:local-service-token}") String token
    ) {
        this.expected = ("Bearer " + token).getBytes(StandardCharsets.UTF_8);
    }

    public void require(String authorization) {
        byte[] actual = authorization == null
                ? new byte[0]
                : authorization.getBytes(StandardCharsets.UTF_8);
        if (!MessageDigest.isEqual(expected, actual)) {
            throw new InternalServiceUnauthorizedException();
        }
    }
}
