from rest_framework.views import APIView


class ShortUrlView(APIView):
    def get(self, request, *args, **kwargs):
        # Get the short URL from the request
        short_url = request.query_params.get('short_url')

        # Get the long URL from the short URL
        # long_url = ShortUrl.objects.get(short_url=short_url).long_url
        #
        # return Response({'long_url': long_url})
