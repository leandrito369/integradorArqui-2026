# Integrador de Arquitectura de Computadoras — 2026

Desarrollo de un procesador **Harvard monociclo de 16 bits**, basado en la consigna del integrador 2025 e inspirado en un subconjunto simplificado de MSP430. El ISA es **propio**, no compatible a nivel binario con MSP430 ni con RISC-V.

> **Estado:** diseño base provisional hasta conocer la consigna específica de 2026. La documentación distingue las exigencias de 2025 de las decisiones del grupo.

## Avance

| Paso | Área | Estado |
|---|---|---|
| 1 | Definición de la ISA | Documentado |
| 2 | Formatos y códigos de instrucción | Diseñado, pendiente validación con cátedra |
| 3 | Datapath | Documentado; simulador funcional probado, Logisim pendiente |
| 4 | ALU y flags | Documentado; 16.972 verificaciones de software correctas, Logisim pendiente |
| 5 | Unidad de control | Documentada; 131.072 combinaciones IR/Z validadas por software |
| 6 | Circuito en Logisim Evolution | **Próximo paso** |
| 7 | Programa de búsqueda y pruebas | Pendiente |
| 8 | Documentación de entrega | Pendiente |

## Documentación

- [Paso 1: ISA y decisiones arquitectónicas](docs/01-isa.md)
- [Paso 2: formatos de instrucción y codificación](docs/02-formatos-instrucciones.md)
- [Paso 3: datapath monociclo y rutas de datos](docs/03-datapath.md)
- [Paso 4: ALU de 16 bits y flags](docs/04-alu-flags.md)
- [Paso 5: unidad de control combinacional](docs/05-unidad-control.md)

## Código y verificación

```bash
python tests/verificar_codificacion.py
python tests/verificar_datapath.py
python tests/verificar_alu.py
python tests/verificar_control.py
```

- `tests/verificar_codificacion.py`: codificación y saltos del programa ilustrativo.
- `tests/simulador_datapath.py` y `tests/verificar_datapath.py`: modelo funcional del procesador y búsqueda lineal (31 comprobaciones).
- `tests/alu_16.py` y `tests/verificar_alu.py`: ALU combinacional y pruebas con casos límite/aleatorios (16.972 comprobaciones).
- `tests/unidad_control.py` y `tests/verificar_control.py`: decodificador combinacional de referencia y tabla exhaustiva de las 65.536 instrucciones por ambos valores de Z (131.072 casos).

Estos programas son **modelos de referencia**, no sustituyen el circuito `.circ` ni su prueba en Logisim.

## Fuentes

- Consigna integrador 2025 aportada por el usuario.
- Apuntes consolidados de las clases 1–6 de Arquitectura de Computadoras (2026).
- Resolución CD 336/25, programa de Arquitectura de Computadoras, vigencia 2026–2029.

## Decisiones relevantes por confirmar

- El mnemónico OR aparece con `^` en la consigna (¿OR inclusivo o XOR?).
- La política de C en resta se fijó provisionalmente como `C=1` cuando hubo préstamo.
- AND/OR fijan C=V=0 por política del grupo.
- Falta adaptar al diseño la ALU original desarrollada previamente en clases; se necesita el circuito `.circ` si está disponible.
- Falta conocer la instrucción particular que se asignará al grupo en 2026.
