# from fabric.widgets.datetime import DateTime

# class DateTime(DateTime):
#     def __init__(self):
#         super().__init__(
#             name="date-time",
#         )
from fabric.widgets.datetime import DateTime

class DateTimeWidget(DateTime):
    def __init__(self):
        super().__init__(
            name="date-time",
            # formatters=[ # AM/PM
            # "%b %-d %-I:%M %p",
            # "%b %-d %-I:%M:%S %p",
            # "%a %-d %Y"],
            formatters = [ # 24 Hours
                "%b %-d %H:%M",
                "%b %-d %H:%M:%S",
                "%a %-d %Y",
            ],
        )

