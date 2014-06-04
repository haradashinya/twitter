from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.messages.storage import session
from django.http import HttpResponse,HttpResponseRedirect
from django.shortcuts import render, redirect
from django.template.defaultfilters import register
from twitter.forms import UserForm, UserProfileForm,TweetForm
from twitter.models import Tweet, UserProfile,Relationship
from django.template.defaultfilters import register
from django.template.defaultfilters import stringfilter
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import Http404
from django.core.exceptions import  ObjectDoesNotExist



PER_TWEET = 20


def index(request):
    _tweets = Tweet.objects.order_by("-created_date").all()
    # show 2 tweets per page
    paginator = Paginator(_tweets,PER_TWEET)
    page = request.GET.get('page') or 1

    try:

        #show public timeline
        tweets = paginator.page(page)
    except EmptyPage:
        tweets = paginator.page(paginator.num_pages)



    if request.session.get("username") is None:
        title = "Dwitter - About"
        return render(request,"twitter/about.html",{
            "title": title
        })
    else:

        title = "Timeline - Dwitter"
        user =  User.objects.get(username = request.session.get("username"))
        return render(request, "twitter/index.html",
            {
                "title": title,
                "login_user": user,
                "tweets": tweets,
                "user": user
            })

def about(request):
    title = "About - Dwitter"
    return render(request, "twitter/about.html",
                  {
                      "title":title
                  }
                  )

def user_edit(request,user_name):
    title = "Timeline - Dwitter"
    user = User.objects.get(username = user_name)
    if request.method == "GET":
        user_form = UserForm(instance=user)
        profile_form = UserProfileForm(instance=user.profile)
        return render(request, "twitter/edit.html",
                      {
                          "user": user,
                          "title": title,
                          "user_form":user_form,
                          "profile_form":profile_form
                      }
                      )
    else:
        user_form = UserForm(data=request.POST,instance=user)
        profile_form = UserProfileForm(data=request.POST,instance=user.profile)
        if user_form.is_valid():
            user_form.save()
            request.session["username"] = request.POST["username"]
            request.session["password"] = request.POST["password"]
        else:
            print(user_form.errors)
            print("INVALID")

        if profile_form.is_valid():
            profile_form.save()

        if 'picture' in request.FILES:
            user.profile.picture = request.FILES['picture']
        user.profile.save()

        return redirect("/{}/edit".format(user.username))


def followings_timeline(request,user_name):
    user = User.objects.get(username = user_name)
    login_user =  User.objects.get(username = request.session.get("username"))
    # follower's users
    users = user.profile.followings()
    __tweets = Tweet.objects.order_by("-created_date").all()
    _tweets = [tweet for tweet in __tweets if tweet.user in users]

    paginator = Paginator(_tweets,PER_TWEET)
    page = request.GET.get('page') or 1
    title = "Timeline - Dwitter"
    try:
        tweets = paginator.page(page)
    except EmptyPage:
        tweets =   paginator.page(paginator.num_pages)

    if user_name == request.session.get("username"):
        user = login_user
    else:
        user = tweets[0].user
    return render(request, "twitter/index.html",
        {
            "tweets": tweets,
            "login_user": login_user,
            "user": user,
            "title": title
        })




def user_register(request):
    registered = False
    if request.method == "POST":
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)
        if user_form.is_valid():
            user = user_form.save()
            request.session["username"] = user.username
            request.session["password"] = user.password
            user.save()

        if profile_form.is_valid():
            profile = profile_form.save(commit=False)
            profile.user = user
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']
            profile.save()
        else:
            print("Error")
            print(profile_form.errors)

        return HttpResponseRedirect("/")


    else:
        title = "Register - Dwitter"
        user_form = UserForm()
        profile_form = UserProfileForm()
        return render(request, "twitter/register.html", {
            "user_form": user_form,
            "profile_form": profile_form,
            "title": title
        })

def relationship(request,user_name):
    whom_user = User.objects.get(username = user_name)
    whom_id = whom_user.id

    who_user =  User.objects.get(username = request.session.get("username"))

    who_id = who_user.id
    if request.method == "POST":

        meth_type = request.POST.get("meth_type")
        if meth_type == "post":
            # follow
            relationship = Relationship.objects.create(who_id=who_id, whom_id = whom_id)
            relationship.save()
            return HttpResponseRedirect("/tweets/{}".format(user_name))
        else:
            # unfollow
            relationship = Relationship.objects.filter(who_id = who_id,whom_id = whom_id).first()
            relationship.delete()
            return HttpResponseRedirect("/tweets/{}".format(user_name))
    elif request.method == "GET":
        user =  User.objects.get(username =  user_name)
        #  show follower/followings by keyward of url.
        _type = request.GET.get("type")
        if _type == "followers":
            rel_users = user.profile.followers()
        else:
            rel_users = user.profile.followings()

        return  render(request,"twitter/relationship_list.html",{
            "login_user": user,
            "rel_users": rel_users,
            "type": _type
        })



@csrf_exempt
def new_tweet(request,user_name):
    if request.method == "GET":
        tweet_form = TweetForm()
        return render(request,"twitter/new_tweet.html",{
            "tweet_form": tweet_form
        })
    else:
        user = User.objects.get_by_natural_key(user_name)
        tweet_form = TweetForm(data = request.POST)
        tweet = tweet_form.save(commit=False)
        tweet.user = user
        tweet.save()
        return HttpResponse("success")


def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = User.objects.filter(username = username,password=password).first()
        if user:
            if user.is_active:
                request.session["username"] = username
                request.session["password"] = password
                return redirect("/")
            else:
                return HttpResponse("Disabled")
        else:
            return HttpResponse("Invalid login")
    else:

        title = "Login - Dwitter"
        return render(request, "twitter/login.html", {
            "title": title
        })


def user_logout(request):
    request.session.pop("username")
    request.session.pop("password")
    return redirect("/")




def user_timeline(request,user_name):
    login_user = User.objects.get(username = request.session.get("username"))


    try:
        user= User.objects.get(username = user_name)
        title = "{} - Dwitter".format(user.username)
    except ObjectDoesNotExist:
        title = None
        raise Http404
    _tweets = user.tweets.order_by("-created_date").all()
    paginator = Paginator(_tweets,PER_TWEET)
    page = request.GET.get('page') or 1
    tweets = paginator.page(page)
    return render(request,"twitter/user.html",{
        "tweets": tweets,
        "user_tweets": user.tweets,
        "title": title,
        "user": user,
        "login_user": login_user
    })
