require 'net/http'
require 'uri'
require 'json'

league_id = "121269"
years = (2010..2024).to_a

File.open("data.js", "w") do |file|
  file.puts "const localLeagueData = {"
  
  years.each_with_index do |year, index|
    uri = URI.parse("https://fantasy.espn.com/apis/v3/games/ffl/leagueHistory/#{league_id}?seasonId=#{year}&view=mMatchupScore&view=mTeam")
    
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = true
    http.verify_mode = OpenSSL::SSL::VERIFY_NONE
    
    req = Net::HTTP::Get.new(uri.request_uri)
    req['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    req['Accept'] = 'application/json'
    
    res = http.request(req)
    
    if res.code == "302" && res['location']
        redir_uri = URI.parse(res['location'])
        redir_http = Net::HTTP.new(redir_uri.host, redir_uri.port)
        redir_http.use_ssl = true
        redir_http.verify_mode = OpenSSL::SSL::VERIFY_NONE
        
        redir_req = Net::HTTP::Get.new(redir_uri.request_uri)
        redir_req['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        redir_req['Accept'] = 'application/json'
        
        res = redir_http.request(redir_req)
    end
    
    if res.code == "200"
      content = res.body
      if content.include?("<html")
          puts "ESPN blocked #{year} - returned HTML"
          file.print "\"#{year}\": {}"
      else
        begin
          data = JSON.parse(content)
          payload = data.is_a?(Array) && data.length > 0 ? data[0] : data
          file.print "\"#{year}\": #{payload.to_json}"
          puts "Success #{year}"
        rescue
          file.print "\"#{year}\": {}"
          puts "Failed parsing #{year}"
        end
      end
    else
      file.print "\"#{year}\": {}"
      puts "Failed request #{year} - Code: #{res.code}"
    end
    
    file.puts "," unless index == 14
    sleep(1.5) # throttle to avoid rate limits
  end
  
  file.puts "\n};"
end
puts "Saved data.js"
