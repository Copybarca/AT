FROM eclipse-temurin:21-jdk-jammy AS dependencies

WORKDIR /workspace

COPY .mvn/ .mvn/
COPY mvnw pom.xml ./

RUN chmod +x mvnw \
    && ./mvnw --no-transfer-progress dependency:go-offline

FROM dependencies AS build

COPY src/ src/

RUN ./mvnw --no-transfer-progress -DskipTests package

FROM eclipse-temurin:21-jre-jammy AS runtime

RUN groupadd --system spring \
    && useradd --system --gid spring --home-dir /app spring

WORKDIR /app

COPY --from=build --chown=spring:spring /workspace/target/trans-api-*.jar app.jar

USER spring:spring

EXPOSE 8080

ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", "-jar", "/app/app.jar"]
