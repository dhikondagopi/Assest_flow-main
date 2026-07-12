from django.urls import path
from apps.bookings.views import (
    BookingListCreateView,
    BookingDetailView,
    CancelBookingView,
    RescheduleBookingView,
    CalendarView,
)

urlpatterns = [
    path("",                        BookingListCreateView.as_view(), name="booking-list"),
    path("calendar/",               CalendarView.as_view(),          name="booking-calendar"),
    path("<uuid:pk>/",              BookingDetailView.as_view(),     name="booking-detail"),
    path("<uuid:pk>/cancel/",       CancelBookingView.as_view(),     name="booking-cancel"),
    path("<uuid:pk>/reschedule/",   RescheduleBookingView.as_view(), name="booking-reschedule"),
]
