FROM personal-twin-workbench:local AS sweethome3d

FROM eclipse-temurin:21-jdk-jammy AS build
WORKDIR /build
COPY --from=sweethome3d /opt/sweethome3d/lib/SweetHome3D.jar /build/SweetHome3D.jar
COPY ConvertHomeXml.java /build/ConvertHomeXml.java
RUN javac -cp /build/SweetHome3D.jar -d /build/classes /build/ConvertHomeXml.java

FROM eclipse-temurin:21-jre-jammy
WORKDIR /app
COPY --from=build /build/SweetHome3D.jar /app/SweetHome3D.jar
COPY --from=build /build/classes/ConvertHomeXml.class /app/ConvertHomeXml.class
ENTRYPOINT ["java", "-cp", "/app:/app/SweetHome3D.jar", "ConvertHomeXml"]
