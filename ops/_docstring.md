# INSTRUCTIONS FOR DOCSTRING MAINTENANCE

1. **Start with a One-Line Summary**
   - The first line should briefly state the function or class’s purpose.

2. **Add a Multi-Line Description (if needed)**
   - If more context is helpful, add a longer explanation after a blank line.

3. **Use Triple Double Quotes**
   - Always use `"""` for docstrings, as recommended by PEP 257 and PEP 8.

4. **Follow the NumPy Docstring Standard**
   - For functions, include these sections:
     - **Parameters**: List each parameter, its type, and a short description (and default if applicable).
     - **Returns**: Describe the return value and its type.
     - **Raises**: List any exceptions the function may raise.
   - For classes, summarize the class, list public methods and instance variables, and document the constructor in `__init__`.

5. **Include Examples**
   - Add usage examples to clarify typical use cases.

6. **Document All Public Functions and Classes**
   - Even if the name is self-explanatory, document the function’s inputs, outputs, and exceptions for clarity, especially in shared or open-source code.

7. **Keep It Concise and Informative**
   - Avoid unnecessary detail, but provide enough context for users to understand how to use the function or class.

8. **Use Consistent Formatting**
   - Stick to the chosen docstring style (NumPy, Google, or reStructuredText) throughout your codebase.

By following these steps, your docstrings will be clear, consistent, and useful for anyone reading or using your code.
