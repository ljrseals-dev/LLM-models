# ONNX-to-Cmajor tool provenance and licensing

## Upstream converter

`onnxToCmajor.py` is derived from the Cmajor project's ONNX converter:

- Upstream source: https://github.com/cmajor-lang/cmajor/blob/main/tools/onnx/onnxToCmajor.py
- Upstream documentation: https://cmajor.dev/docs/Tools/MachineLearning
- Upstream licence terms: https://github.com/cmajor-lang/cmajor/blob/main/LICENSE.md
- Upstream licensing-change commit: https://github.com/cmajor-lang/cmajor/commit/fca231d743531762ed34878c31bda456f81b40ca
- Schema reference copy: https://github.com/ljrseals-dev/schema/blob/main/tools/onnx/onnxToCmajor.py

The upstream file identifies Cmajor Software Ltd. as copyright holder and states that Cmajor is available under GPLv3-or-later or a commercial licence. The copy in the schema repository retains that header. Its later modifications in the schema repository do not, by themselves, relicense the upstream-derived portions.

Accordingly, this repository does **not** represent the upstream converter or its derivative as MIT-licensed. Retain the upstream copyright and licence notices and comply with the applicable Cmajor terms unless written permission from the relevant copyright holder authorizes different terms.

## Cmajor templates

The bundled files `patchTemplate/model.cmajor`, `patchTemplate/model.cmajorpatch`, and `patchTemplate/onnx.cmajor` originate from the Cmajor project and are subject to the applicable Cmajor GPLv3-or-later or commercial terms. See the upstream licence file above.

## MIT-licensed schema components

The independent fallback implementation copied from `ljrseals-dev/schema`, `src/schema_review/fallback_runtime.py`, is covered by the MIT licence in that repository:

- Schema repository licence: https://github.com/ljrseals-dev/schema/blob/main/LICENSE
- Fallback implementation: https://github.com/ljrseals-dev/schema/blob/main/src/schema_review/fallback_runtime.py

The MIT licence applies to that schema-owned component and other original work for which the repository owner holds the necessary rights. It does not override the Cmajor terms for the upstream-derived converter or templates.

## If an MIT-only distribution is required

Do not simply change the licence header. Either obtain written relicensing permission from Cmajor Software Ltd. for the converter and templates, or replace the upstream-derived files with a clean-room implementation written independently from the documented ONNX/Cmajor interfaces. The latter must not copy protected implementation code or templates.
