"""The customer-facing edge of the money engine.

Everything in here translates HTTP and nothing else. Not one view creates an
entry, decides an amount, or reads a customer's identity from anywhere but the
authenticated token.
"""
