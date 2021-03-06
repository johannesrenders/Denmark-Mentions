# -*- coding: utf-8 -*-

from collections import defaultdict
import time
import datetime
import xlwt

from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone
from django.http import HttpResponse

from app.forms import Form
from app.models import Fbcomment, Fbpost, Ytcomment


def main(request):
    if request.method == 'POST':
        form = Form(request.POST)
        if form.is_valid():
            keywords = form.cleaned_data.get('keywords')
            timestamp = form.cleaned_data.get('date')
            export = form.cleaned_data.get('export_to_excel')
            results = search(keywords, timestamp)
        else:
            results = defaultdict(int)
            keywords = "ERROR!!!"
        context = {
            'form': form,
            'fb_comments': results['fb_comments'],
            'fb_comments_count': results['fb_comments_count'],
            'fb_posts': results['fb_posts'],
            'fb_posts_count': results['fb_posts_count'],
            'yt_comments': results['yt_comments'],
            'yt_comments_count': results['yt_comments_count']
        }
        if export:
            return export_to_excel(keywords, context)
        # print('context:', context)
        return render(request, 'template.html', context)
    form = Form()
    return render(request, 'template.html', {
        'form': form
    })

def search(keywords, timestamp):
    keywords = keywords.split()
    if timestamp:
        time_tuple = datetime.datetime.strptime(timestamp, '%d-%m-%Y').timetuple()
        timestamp = time.mktime(time_tuple)
        timestamp = datetime.datetime.fromtimestamp(timestamp)
        timestamp = timezone.make_aware(timestamp)
        print "timestamp:", timestamp
    qset = Q()
    for keyword in keywords:
        qset |= Q(message__icontains=keyword)
    if timestamp:
        nqset = qset & Q(timestamp__gt=timestamp)
    else:
        nqset = qset
    valid_fb_posts = list(Fbpost.objects.filter(nqset))
    valid_fb_comments = list(Fbcomment.objects.filter(nqset))
    valid_yt_comments = list(Ytcomment.objects.filter(nqset))
    sort_by_key_occ(valid_fb_posts, keywords)
    sort_by_key_occ(valid_fb_comments, keywords)
    sort_by_key_occ(valid_yt_comments, keywords)
    return {
        'fb_comments': valid_fb_comments,
        'fb_comments_count': len(valid_fb_comments),
        'fb_posts': valid_fb_posts,
        'fb_posts_count': len(valid_fb_posts),
        'yt_comments': valid_yt_comments,
        'yt_comments_count': len(valid_yt_comments)
    }

def export_to_excel(keywords, context):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="results.xls"'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Users')
    row_num = 0
    count_total = context['fb_comments_count'] + \
            context['fb_posts_count'] + context['yt_comments_count']
    font = xlwt.XFStyle()
    bold_font = xlwt.XFStyle()
    bold_font.bold = True
    ws.write(0, 0, "SEARCH RESULTS", bold_font)
    ws.write(0, 1, count_total, bold_font)
    ws.write(1, 0, "KEYWORDS", bold_font)
    ws.write(1, 1, keywords, bold_font)

    ws.write(4, 0, "Facebook Comments", bold_font)
    ws.write(4, 1, context['fb_comments_count'], bold_font)
    cols = ['id', 'username', 'timestamp', 'message']
    for col_num in xrange(len(cols)):
        ws.write(5, col_num, cols[col_num], bold_font)
    row_num = 6
    for comment in context['fb_comments']:
        ws.write(row_num, 0, comment.comment_id, font)
        ws.write(row_num, 1, comment.username, font)
        ws.write(row_num, 2, str(comment.timestamp), font)
        ws.write(row_num, 3, comment.message, font)
        row_num += 1

    row_num += 1
    ws.write(row_num, 0, "Facebook Posts", bold_font)
    ws.write(row_num, 1, context['fb_posts_count'], bold_font)
    row_num += 1
    cols = ['id', 'pagename', 'timestamp', 'message']
    for col_num in xrange(len(cols)):
        ws.write(row_num, col_num, cols[col_num], bold_font)
    row_num += 1
    for post in context['fb_posts']:
        ws.write(row_num, 0, post.post_id, font)
        ws.write(row_num, 1, post.pagename, font)
        ws.write(row_num, 2, str(post.timestamp), font)
        ws.write(row_num, 3, post.message, font)
        row_num += 1

    row_num += 1
    ws.write(row_num, 0, 'Youtube Comments', bold_font)
    ws.write(row_num, 1, context['yt_comments_count'], bold_font)
    row_num += 1
    cols = ['id', 'username', 'timestamp', 'video', 'comment']
    for col_num in xrange(len(cols)):
        ws.write(row_num, col_num, cols[col_num], bold_font)
    row_num += 1
    for comment in context['yt_comments']:
        ws.write(row_num, 0, comment.comment_id, font)
        ws.write(row_num, 1, comment.username, font)
        ws.write(row_num, 2, str(comment.timestamp), font)
        ws.write(row_num, 3, comment.video, font)
        ws.write(row_num, 4, comment.message, font)
        row_num += 1

    wb.save(response)
    return response


def sort_by_key_occ(obj_list, keywords):
    for i in xrange(len(obj_list)):
        freq = 0
        for keyword in keywords:
            if keyword in obj_list[i].message:
                freq += 1
        obj_list[i] = (freq, obj_list[i])
    obj_list.sort(key=lambda x: x[0], reverse=True)
    for i in xrange(len(obj_list)):
        obj_list[i] = obj_list[i][1]
