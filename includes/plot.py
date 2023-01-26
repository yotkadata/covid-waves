#
# Function to calculate quintiles for the colorscale
#
def calc_quantiles(df_q, column_q, normalized=True, base=5):
    # Steps to be used as break points
    steps = [0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 0.99, 1]
    breaks_q = {}

    for step in range(len(steps)):
        # Calculate quantiles based on the steps defined above
        breaks_q[steps[step]] = df_q[column_q].quantile(steps[step])

        # Round to next integer for low values (method from https://stackoverflow.com/a/2272174)
        if breaks_q[steps[step]] < (1.5 * base):
            breaks_q[steps[step]] = round(df_q[column_q].quantile(steps[step]))
        # Round to next base for higher values
        if (1.5 * base) <= breaks_q[steps[step]] < (10 * base):
            breaks_q[steps[step]] = base * round(df_q[column_q].quantile(steps[step]) / base)
        # Round to twice the base for very high values
        if breaks_q[steps[step]] >= 10 * base:
            breaks_q[steps[step]] = (2 * base) * round(df_q[column_q].quantile(steps[step]) / (2 * base))

        # Normalize to values between 0 and 1 if selected
        if normalized:
            breaks_q[steps[step]] = (breaks_q[steps[step]] / df_q[column_q].max()).round(3)

    return breaks_q
