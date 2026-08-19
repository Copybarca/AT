package io.copybarca.transapi.service;

public class InternalServiceUnauthorizedException extends RuntimeException {

    public InternalServiceUnauthorizedException() {
        super("Internal service token is invalid");
    }
}
