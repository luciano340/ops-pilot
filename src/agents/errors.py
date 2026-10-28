class StructuredOutputError(RuntimeError):
    """Raised when a model response cannot be validated against its schema."""

    def __init__(self) -> None:
        super().__init__(
            "The model returned an invalid structured response. Please retry "
            "or choose a model that supports structured outputs."
        )
