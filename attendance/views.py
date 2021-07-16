from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from attendance import recognize as rec, data_creator as dc, train_model
from attendance.models import Account, Organization, Department, Attendance, Attendance_Config, Cards, Payments
from django.contrib.auth import get_user_model
from wsgiref.util import FileWrapper
import os

from django.core.exceptions import FieldDoesNotExist
import django_filters.rest_framework
from rest_framework import generics, mixins, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework import status
# from rest_framework import status

from .serializers import DepartmentSerializer, OrganizationSerializer, AccountSerializer, CardsSerializer
from .serializers import AttendanceSerializer, Attendance_ConfigSerializer, UserSerializer , PaymentsSerializer

import numpy as np
import urllib
import json
import razorpay
import cv2
import pandas as pd
import datetime
from io import BytesIO


def home(request):
    return render(request, 'home.html')

# class AccountList(APIView):
#     def get(self, request, format=None):
#         emp = AccountSerializer(Account.objects.all(),many=True)
#         return Response(emp.data)

#     def post(self,request, format=None):
#         emp = AccountSerializer(data=request.data)
#         if emp.is_valid():
#             emp.save()
#             return Response(emp.data, status=status.HTTP_201_CREATED)
#         return Response(emp.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateUserView(mixins.CreateModelMixin, generics.ListAPIView):
    model = get_user_model()
    permission_classes = [
        permissions.AllowAny  # Or anon users can't register
    ]
    serializer_class = UserSerializer

    def get_queryset(self):
        usermodel = get_user_model()
        return usermodel.objects.all()

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class AccountRegister(generics.CreateAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    parser_classes = [FormParser, MultiPartParser, JSONParser]

    # filter_backends     = filter_backends = [filters.SearchFilter]
    # search_fields       = ['username', 'email', 'role']


class AccountList(generics.ListAPIView):
    lookup_field = 'empId'
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    # extra_kwargs = {
    #         'url': {'view_name': 'account', 'lookup_field': 'pk'},
    #     }


class AccountFilter(generics.ListAPIView):
    serializer_class = AccountSerializer

    def get_queryset(self):
        """
        This view should return a list of all the purchases for
        the user as determined by the username portion of the URL.
        """
        queryset = Account.objects.all()
        role = self.request.query_params.get('role', None)
        orgId = self.request.query_params.get('orgId', None)
        emailId = self.request.query_params.get('email', None)

        if role is not None:
            queryset = queryset.filter(role__exact=role)
        if orgId is not None:
            queryset = queryset.filter(orgId__exact=orgId)
        if emailId is not None:
            queryset = queryset.filter(emailId__exact=emailId)
        return queryset


class AccountDetail(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'empId'
    queryset = Account.objects.all().order_by('empId')
    serializer_class = AccountSerializer


class OrganizationList(generics.ListCreateAPIView):
    lookup_field = 'pk'
    parser_classes = [FormParser, MultiPartParser]
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


class OrganizationDetail(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'pk'
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


class DepartmentList(generics.ListCreateAPIView):

    def get_queryset(self):
        queryset = Department.objects.all()

        orgId = self.request.query_params.get('orgId', None)

        if orgId is not None:
            queryset = Department.objects.filter()
            for i in Department.objects.all():
                if (i.account_set.filter(orgId=orgId)):
                    queryset.add(i)
            print(queryset)
        return queryset

    serializer_class = DepartmentSerializer


class DepartmentDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class AttendanceList(generics.ListCreateAPIView):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer


class AttendanceDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer


class Attendance_ConfigList(generics.ListCreateAPIView):
    queryset = Attendance_Config.objects.all()
    serializer_class = Attendance_ConfigSerializer


class AttendanceFilter(generics.ListAPIView):
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        """
        This view should return a list of all the purchases for
        the user as determined by the username portion of the URL.
        """
        queryset = Attendance.objects.all().order_by('date')
        empId = self.request.query_params.get('empId', None)
        if empId is not None:
            queryset = queryset.filter(empId__exact=empId)
        return queryset

class PaymentsList(generics.ListAPIView):
    queryset = Payments.objects.all()
    serializer_class = PaymentsSerializer

class CardsList(generics.ListAPIView):
    queryset = Cards.objects.all()
    serializer_class = CardsSerializer

class PaymentsDetail(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'pk'
    queryset = Payments.objects.all()
    serializer_class = PaymentsSerializer

class CardsDetail(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'pk'
    queryset = Cards.objects.all()
    serializer_class = CardsSerializer


@csrf_exempt
def detect(request):
    # initialize the data dictionary to be returned by the request
    data = {"success": False}
    id = None
    # check to see if this is a post request
    if request.method == "POST":
        # check to see if an image was uploaded
        if request.FILES.get("image", None) is not None:
            # grab the uploaded image
            image = _grab_image(stream=request.FILES["image"])
        # otherwise, assume that a URL was passed in
        else:
            # grab the URL from the request
            req = request.POST.get("id", None)
            # if the URL is None, then return an error
            if req is None:
                data["error"] = "No URL provided."
                return JsonResponse(data)
            id = request.POST["id"]
            print(id)
            # load the image and convert
            # image = _grab_image(url=url)
        if id is None:
            result = rec.predict_face(image)
            if result["error"] != '':
                data["success"] = False
                data["result"] = result
            else:
                # data.update({'result': result})
                data = fetch_details(result['name'], result['accuracy'])
        else:
            data = fetch_details(id)

    # return a JSON response
    return JsonResponse(data)


def fetch_details(id, acc=''):
    data = {}
    data["success"] = True
    account = Account.objects.all()
    account.order_by('empId')
    if int(id) not in range(int(account.first().empId), int(account.last().empId)):
        data['error'] = "Employee ID is not valid"
        data["success"] = "False"
        return data
    res = {}
    res['empId'] = id
    res['firstName'] = account.get(empId=int(id)).firstName
    res['lastName'] = account.get(empId=int(id)).lastName
    res['accuracy'] = acc
    data['result'] = res
    return data


def _grab_image(path=None, stream=None, url=None):
    # if the path is not None, then load the image from disk
    if path is not None:
        image = cv2.imread(path)
    # otherwise, the image does not reside on disk
    else:
        # if the URL is not None, then download the image
        if url is not None:
            resp = urllib.urlopen(url)
            data = resp.read()
        # if the stream is not None, then the image has been uploaded
        elif stream is not None:
            data = stream.read()
        # convert the image to a NumPy array and then read it into
        # OpenCV format
        image = np.asarray(bytearray(data), dtype="uint8")
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)

    # return the image
    return image


@csrf_exempt
def train_dataset(request):
    name = request.POST['empId']
    # if request.FILES.get("image", None) is not None:
    # grab the uploaded image
    # image = _grab_image(stream=request.FILES["image"])
    images = dict((request.FILES).lists())['image']
    for i in images:
        image = _grab_image(stream=i)

        dc.create_dataset(name, image)

    train_model.create_model()
    return JsonResponse({"status": "success, dataset and model created successfully"})


@csrf_exempt
def report_att(request):
    report = {}
    empids = set()
    orgId = request.GET['orgId']
    month = request.GET['month']

    # employee = Account.objects.raw(f'select * from attendance_account where orgId_id={orgId}')
    employee = Account.objects.filter(orgId=orgId)
    for i in employee:
        empids.add(i.empId)

    for i in empids:
        # query = Attendance.objects.raw(f'select * from attendance_attendance where empId_id={i}')
        query = Attendance.objects.filter(empId=i)
        days = [0]*31
        for j in query:
            if j.date.month == int(month):
                if j.leave == 0:
                    days[j.date.day-1] = 1
                else:
                    days[j.date.day-1] = -1
        report[f'{i}'] = days
    return JsonResponse(report)


@csrf_exempt
def daily_report(request):
    orgId = request.GET['orgId']
    date = request.GET['date']

    empids = set()
    # employee = Account.objects.raw(f'select * from attendance_account where orgId_id={orgId}')
    employee = Account.objects.filter(orgId=orgId)
    for i in employee:
        empids.add(i.empId)

    present, absent, leave = [0, 0, 0]
    for j in empids:
        # attendance = Attendance.objects.raw(f'select * from attendance_attendance where date="{date}" and empId_id={j}')
        attendance = Attendance.objects.filter(date=date, empId=j)
        print(attendance)
        for i in attendance:
            if i.leave == 0:
                present += 1
            else:
                leave += 1

    absent = len(empids) - (present + leave)

    report = {'present': present, 'absent': absent, 'leave': leave}

    return JsonResponse(report)


@csrf_exempt
def report_download(request):
    # a = {"111": [0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}
    # a['121'] = [0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    report = {}
    empids = set()
    orgId = request.GET['orgId']
    month = request.GET['month']

    # employee = Account.objects.raw(f'select * from attendance_account where orgId_id={orgId}')
    employee = Account.objects.filter(orgId=orgId)
    for i in employee:
        empids.add(i.empId)

    for i in empids:
        # query = Attendance.objects.raw(f'select * from attendance_attendance where empId_id={i}')
        query = Attendance.objects.filter(empId=i)
        days = ['Absent']*31
        for j in query:
            if j.date.month == int(month):
                if j.leave == 0:
                    days[j.date.day-1] = 'Present'
                else:
                    days[j.date.day-1] = 'On Leave'
        days.insert(0, days.count('On Leave'))
        days.insert(0, days.count('Absent'))
        days.insert(0, days.count('Present'))
        report[f'{i}'] = days

    column = [str(i) for i in range(1, 32)]
    column.insert(0, 'Emp_ID')
    column.insert(1, 'Leaves')
    column.insert(1, 'Absent')
    column.insert(1, 'Present')

    rows = []
    for i in report:
        temp = report[i]
        temp.insert(0, i)
        rows.append(temp)

    df = pd.DataFrame(rows, columns=column)

    df.to_csv('download_file.csv', index=False)

    response = HttpResponse(FileWrapper(
        open(os.getcwd() + '/download_file.csv')), content_type='text/csv')
    filename = 'Report-' + str(datetime.datetime.now().date()) + \
        '-' + str(datetime.datetime.now().time())[:8].replace(':', '.')
    response['Content-Disposition'] = f'attachment; filename={filename}.csv'
    os.system('rm download_file.csv')
    return response


@csrf_exempt
def payment_gateway(request):
    payment_id = request.GET['payment_id']
    amount = int(request.GET['amount'])*100

    client = razorpay.Client(auth=('rzp_test_wHJx64AAevdTiq','JRIPoQXmHu97e9J9Bjkdsi7v'))
    respond = client.payment.capture(payment_id, f'{amount}', {"currency": "INR"})

    return JsonResponse(respond)
