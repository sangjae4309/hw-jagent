# C/C++ style

## C and C++ Style

- Do not introduce custom C or C++ templates, template specializations, or
  template-based dispatch. Use ordinary functions and explicit loops instead.
  This does not prohibit using existing library types such as ap_uint or
  hls::stream. Do not replace a loop with a long list of numbered template calls.

- Do not implement hardware structure or control flow with recursive functions
  or recursive template dispatch. Use explicit loops, stages, and module calls
  so the source directly shows the intended hardware organization.
- Size hardware counters, indices, and addresses to their actual ranges rather
  than defaulting to `int`. Loop counter widths must include the termination
  value; widen arithmetic explicitly before operations that could overflow.
- Do not use `#if`, `#ifdef`, or `#ifndef` to select optional C or C++
  implementation paths, data members, function parameters, or design-variant
  behavior. Give each design variant one unconditional interface and source
  path. Preprocessor conditionals are permitted only for conventional header
  guards, required platform/tool compatibility, and build-time configuration
  declaration or validation; they must not branch a design implementation or
  ABI.
- Do not use hard tab characters in C or C++ source files.
- Indent continuation lines by four additional spaces.
- Use braces for every `for`, `while`, and conditional body.
- Place function-definition opening braces on the line after the declaration.
- Place opening braces for `for`, `while`, and conditional statements on the
  same line as the control statement.
- Keep the initializer, condition, and increment of each `for` statement on
  one line.
- Put each loop label on the same line as the `for` statement it identifies,
  in the form `LOOP_NAME: for (...)`.
- Name every function that returns a value with a verb-led name, such as
  `calculate_offset()`. Do not use noun-only or adjective-led names for
  value-returning functions.
- Do not create trivial pass-through or accessor helper functions that only
  return a constant, cast, field, bit, or range. Access or initialize that
  value directly at the use site unless the helper provides meaningful reused
  behavior or abstraction.
- Before using `{}` zero-initialization on a local array or aggregate, verify
  that the zero value is semantically consumed before every element is
  overwritten. In Vitis HLS, do not zero-initialize fully partitioned
  temporaries whose consumed elements are already written before use, because
  the implicit initialization loop can serialize otherwise parallel hardware.
  When only some paths need a default, initialize only the elements on those
  paths.
- Keep C and C++ statements, expressions, declarations, control conditions,
  function declarations, and function calls on one line when the resulting
  line is at most 120 characters.
- Split C and C++ code across multiple lines only when its single-line form
  would exceed 120 characters. When a function declaration or call must be
  split, break it only at natural boundaries and keep as many arguments as fit
  on each line. Do not mechanically place every argument on its own line.

Read ../code-pitfall/hls-signed-index.md when these types control HLS addressing.
