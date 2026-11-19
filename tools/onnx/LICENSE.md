# Cmajor ONNX tool licensing

The files in this directory include code and templates from the Cmajor project, copyright Cmajor Software Ltd. The upstream Cmajor project publishes these files under either the GNU General Public License version 3 or later (GPL-3.0-or-later), or a commercial licence. See the upstream Cmajor LICENSE.md at https://github.com/cmajor-lang/cmajor/blob/main/LICENSE.md and commercial licence options at https://cmajor.dev/docs/Licence.

The following files are Cmajor-origin files or derived from them and retain their upstream copyright/licensing notices:

- onnxToCmajor.py
- patchTemplate/model.cmajor
- patchTemplate/model.cmajorpatch
- patchTemplate/onnx.cmajor

This tool is kept in its own directory because it has licensing terms distinct from the rest of this repository. Do not remove or override the Cmajor notices. Users distributing or modifying these files must comply with GPL-3.0-or-later or obtain the appropriate commercial licence from Cmajor Software Ltd.

The numeric fallback implementation at src/schema_review/fallback_runtime.py is from ljrseals-dev/schema and is distributed under that repository's MIT licence. It is separately licensed from the Cmajor-origin files.
